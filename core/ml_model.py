from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from core.database import get_connection
from core.priority import importance_score, normalize_priority

MODEL_NAME = "Ridge Regression"
MIN_TRAINING_SAMPLES = 8

FEATURE_NAMES = [
    "planned_duration",
    "priority",
    "days_to_deadline",
    "weekend_deadline",
]

MODEL_DIR = Path(__file__).resolve().parent / "models"
MODEL_PATH = MODEL_DIR / "duration_ridge_model.joblib"


@dataclass
class MLModelStatus:
    trained: bool
    samples: int
    mae: float | None
    updated_at: str | None
    message: str
    model_name: str = MODEL_NAME
    min_samples: int = MIN_TRAINING_SAMPLES

    def to_dict(self) -> dict[str, Any]:
        return {
            "trained": self.trained,
            "samples": self.samples,
            "mae": self.mae,
            "updated_at": self.updated_at,
            "message": self.message,
            "model_name": self.model_name,
            "min_samples": self.min_samples,
            "feature_names": FEATURE_NAMES,
        }


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_date(value: Any) -> date | None:
    if not value:
        return None

    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def calculate_duration_features(
    planned_duration: int,
    priority: int,
    deadline: str,
    reference_date: date | None = None,
) -> dict[str, int]:
    """
    Features used by the supervised duration model.

    User-facing priority:
    P1 = most important
    P5 = least important

    ML feature 'priority':
    P1 -> 5
    P2 -> 4
    P3 -> 3
    P4 -> 2
    P5 -> 1
    """
    reference_date = reference_date or date.today()
    deadline_date = _parse_date(deadline)

    if deadline_date is None:
        days_to_deadline = 0
        weekend_deadline = 0
    else:
        days_to_deadline = (deadline_date - reference_date).days
        weekend_deadline = 1 if deadline_date.weekday() >= 5 else 0

    normalized_priority = normalize_priority(priority)

    return {
        "planned_duration": max(1, _safe_int(planned_duration, 1)),
        "priority": importance_score(normalized_priority),
        "days_to_deadline": days_to_deadline,
        "weekend_deadline": weekend_deadline,
    }


def _feature_vector(features: dict[str, int]) -> list[float]:
    return [float(features[name]) for name in FEATURE_NAMES]


def build_feature_vector(
    planned_duration: int,
    priority: int,
    deadline: str,
    reference_date: date | None = None,
) -> list[float]:
    features = calculate_duration_features(
        planned_duration=planned_duration,
        priority=priority,
        deadline=deadline,
        reference_date=reference_date,
    )

    return _feature_vector(features)


def _update_model_status(
    trained: bool,
    samples: int,
    mae: float | None,
    message: str,
):
    updated_at = datetime.now().isoformat(timespec="seconds")

    with get_connection() as conn:
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO ml_model_status (
                id,
                model_name,
                trained,
                samples,
                mae,
                updated_at,
                message
            )
            VALUES (1, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                model_name = excluded.model_name,
                trained = excluded.trained,
                samples = excluded.samples,
                mae = excluded.mae,
                updated_at = excluded.updated_at,
                message = excluded.message
        """, (
            MODEL_NAME,
            1 if trained else 0,
            int(samples),
            float(mae) if mae is not None else None,
            updated_at,
            message,
        ))

        conn.commit()


def get_model_status() -> MLModelStatus:
    with get_connection() as conn:
        cur = conn.cursor()

        cur.execute("""
            SELECT model_name, trained, samples, mae, updated_at, message
            FROM ml_model_status
            WHERE id = 1
        """)

        row = cur.fetchone()

    if row is None:
        return MLModelStatus(
            trained=False,
            samples=0,
            mae=None,
            updated_at=None,
            message="Model status row does not exist yet.",
        )

    return MLModelStatus(
        trained=bool(row["trained"]),
        samples=_safe_int(row["samples"], 0),
        mae=_safe_float(row["mae"]),
        updated_at=row["updated_at"],
        message=row["message"] or "",
        model_name=row["model_name"] or MODEL_NAME,
    )


def _get_training_rows(limit: int = 1000) -> list[dict[str, Any]]:
    with get_connection() as conn:
        cur = conn.cursor()

        cur.execute("""
            SELECT
                priority,
                planned_duration,
                actual_duration,
                deadline,
                completed_at,
                created_at,
                days_to_deadline,
                weekend_deadline
            FROM task_history
            WHERE
                priority IS NOT NULL
                AND planned_duration IS NOT NULL
                AND actual_duration IS NOT NULL
            ORDER BY id DESC
            LIMIT ?
        """, (int(limit),))

        rows = cur.fetchall()

    training_rows: list[dict[str, Any]] = []

    for row in rows:
        planned_duration = _safe_int(row["planned_duration"], 0)
        actual_duration = _safe_int(row["actual_duration"], 0)
        priority = normalize_priority(row["priority"])

        if planned_duration <= 0 or actual_duration <= 0:
            continue

        days_to_deadline = row["days_to_deadline"]
        weekend_deadline = row["weekend_deadline"]

        if days_to_deadline is None or weekend_deadline is None:
            reference_date = _parse_date(row["created_at"]) or _parse_date(row["completed_at"]) or date.today()

            features = calculate_duration_features(
                planned_duration=planned_duration,
                priority=priority,
                deadline=row["deadline"],
                reference_date=reference_date,
            )
        else:
            features = {
                "planned_duration": planned_duration,
                "priority": importance_score(priority),
                "days_to_deadline": _safe_int(days_to_deadline, 0),
                "weekend_deadline": _safe_int(weekend_deadline, 0),
            }

        training_rows.append({
            "features": features,
            "target": actual_duration,
        })

    return training_rows


def train_duration_model(min_samples: int = MIN_TRAINING_SAMPLES) -> MLModelStatus:
    rows = _get_training_rows()
    samples = len(rows)

    if samples < min_samples:
        message = (
            f"Cold start: {samples}/{min_samples} history samples available. "
            "Model will train automatically after more completed tasks."
        )

        _update_model_status(
            trained=False,
            samples=samples,
            mae=None,
            message=message,
        )

        return get_model_status()

    try:
        from joblib import dump
        from sklearn.linear_model import Ridge
        from sklearn.metrics import mean_absolute_error
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler
    except Exception as exc:
        _update_model_status(
            trained=False,
            samples=samples,
            mae=None,
            message=f"ML dependencies are missing or unavailable: {exc}",
        )

        return get_model_status()

    X = [_feature_vector(row["features"]) for row in rows]
    y = [float(row["target"]) for row in rows]

    model = Pipeline([
        ("scaler", StandardScaler()),
        ("ridge", Ridge(alpha=1.0)),
    ])

    model.fit(X, y)

    predictions = model.predict(X)
    mae = float(mean_absolute_error(y, predictions))

    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    dump({
        "model": model,
        "feature_names": FEATURE_NAMES,
        "trained_at": datetime.now().isoformat(timespec="seconds"),
        "samples": samples,
        "mae": mae,
        "model_name": MODEL_NAME,
    }, MODEL_PATH)

    _update_model_status(
        trained=True,
        samples=samples,
        mae=round(mae, 2),
        message="Model trained successfully from task_history.",
    )

    return get_model_status()


def retrain_duration_model() -> MLModelStatus:
    return train_duration_model()


def predict_duration_with_model(
    planned_duration: int,
    priority: int,
    deadline: str,
) -> dict[str, Any] | None:
    status = get_model_status()

    if not status.trained or status.samples < MIN_TRAINING_SAMPLES:
        status = train_duration_model()

    if not status.trained:
        return None

    if not MODEL_PATH.exists():
        status = train_duration_model()

        if not status.trained or not MODEL_PATH.exists():
            return None

    try:
        from joblib import load
    except Exception:
        return None

    payload = load(MODEL_PATH)
    model = payload["model"]

    features = calculate_duration_features(
        planned_duration=planned_duration,
        priority=priority,
        deadline=deadline,
    )

    X = [_feature_vector(features)]
    prediction = float(model.predict(X)[0])

    recommended = int(round(max(5.0, prediction)))

    return {
        "recommended": recommended,
        "features": features,
        "samples": status.samples,
        "mae": status.mae,
        "model_name": status.model_name,
        "trained": status.trained,
        "updated_at": status.updated_at,
    }