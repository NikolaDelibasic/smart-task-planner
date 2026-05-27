from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from core.database import get_connection
from core.priority import importance_score, normalize_priority

MODEL_NAME = "Logistic Regression Risk Model"
MIN_RISK_SAMPLES = 12

FEATURE_NAMES = [
    "planned_duration",
    "priority",
    "days_to_deadline",
    "weekend_deadline",
]

MODEL_DIR = Path(__file__).resolve().parent / "models"
MODEL_PATH = MODEL_DIR / "risk_models.joblib"


@dataclass
class RiskModelStatus:
    trained: bool
    samples: int
    overtime_accuracy: float | None
    late_accuracy: float | None
    updated_at: str | None
    message: str
    model_name: str = MODEL_NAME
    min_samples: int = MIN_RISK_SAMPLES

    def to_dict(self) -> dict[str, Any]:
        return {
            "trained": self.trained,
            "samples": self.samples,
            "overtime_accuracy": self.overtime_accuracy,
            "late_accuracy": self.late_accuracy,
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


def _ensure_status_table():
    with get_connection() as conn:
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS risk_model_status (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                model_name TEXT NOT NULL,
                trained INTEGER NOT NULL DEFAULT 0,
                samples INTEGER NOT NULL DEFAULT 0,
                overtime_accuracy REAL,
                late_accuracy REAL,
                updated_at TEXT,
                message TEXT
            )
        """)

        cur.execute("""
            INSERT OR IGNORE INTO risk_model_status (
                id,
                model_name,
                trained,
                samples,
                overtime_accuracy,
                late_accuracy,
                updated_at,
                message
            )
            VALUES (
                1,
                ?,
                0,
                0,
                NULL,
                NULL,
                NULL,
                'Risk model is not trained yet.'
            )
        """, (MODEL_NAME,))

        conn.commit()


def _update_status(
    trained: bool,
    samples: int,
    overtime_accuracy: float | None,
    late_accuracy: float | None,
    message: str,
):
    _ensure_status_table()

    updated_at = datetime.now().isoformat(timespec="seconds")

    with get_connection() as conn:
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO risk_model_status (
                id,
                model_name,
                trained,
                samples,
                overtime_accuracy,
                late_accuracy,
                updated_at,
                message
            )
            VALUES (1, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                model_name = excluded.model_name,
                trained = excluded.trained,
                samples = excluded.samples,
                overtime_accuracy = excluded.overtime_accuracy,
                late_accuracy = excluded.late_accuracy,
                updated_at = excluded.updated_at,
                message = excluded.message
        """, (
            MODEL_NAME,
            1 if trained else 0,
            int(samples),
            float(overtime_accuracy) if overtime_accuracy is not None else None,
            float(late_accuracy) if late_accuracy is not None else None,
            updated_at,
            message,
        ))

        conn.commit()


def get_risk_model_status() -> RiskModelStatus:
    _ensure_status_table()

    with get_connection() as conn:
        cur = conn.cursor()

        cur.execute("""
            SELECT
                model_name,
                trained,
                samples,
                overtime_accuracy,
                late_accuracy,
                updated_at,
                message
            FROM risk_model_status
            WHERE id = 1
        """)

        row = cur.fetchone()

    if row is None:
        return RiskModelStatus(
            trained=False,
            samples=0,
            overtime_accuracy=None,
            late_accuracy=None,
            updated_at=None,
            message="Risk model status row does not exist yet.",
        )

    return RiskModelStatus(
        trained=bool(row["trained"]),
        samples=_safe_int(row["samples"], 0),
        overtime_accuracy=_safe_float(row["overtime_accuracy"]),
        late_accuracy=_safe_float(row["late_accuracy"]),
        updated_at=row["updated_at"],
        message=row["message"] or "",
        model_name=row["model_name"] or MODEL_NAME,
    )


def calculate_risk_features(
    planned_duration: int,
    priority: int,
    deadline: str,
    reference_date: date | None = None,
) -> dict[str, int]:
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


def _risk_bucket(probability: float) -> str:
    if probability >= 0.75:
        return "high"

    if probability >= 0.45:
        return "medium"

    return "low"


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
                AND deadline IS NOT NULL
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

        deadline_date = _parse_date(row["deadline"])
        completed_date = _parse_date(row["completed_at"])

        if deadline_date is None or completed_date is None:
            continue

        created_date = _parse_date(row["created_at"]) or completed_date

        if row["days_to_deadline"] is not None and row["weekend_deadline"] is not None:
            features = {
                "planned_duration": planned_duration,
                "priority": importance_score(priority),
                "days_to_deadline": _safe_int(row["days_to_deadline"], 0),
                "weekend_deadline": _safe_int(row["weekend_deadline"], 0),
            }
        else:
            features = calculate_risk_features(
                planned_duration=planned_duration,
                priority=priority,
                deadline=row["deadline"],
                reference_date=created_date,
            )

        overtime_label = 1 if actual_duration > planned_duration else 0
        late_label = 1 if completed_date > deadline_date else 0

        training_rows.append({
            "features": features,
            "overtime_label": overtime_label,
            "late_label": late_label,
        })

    return training_rows


def retrain_risk_models(min_samples: int = MIN_RISK_SAMPLES) -> RiskModelStatus:
    rows = _get_training_rows()
    samples = len(rows)

    if samples < min_samples:
        _update_status(
            trained=False,
            samples=samples,
            overtime_accuracy=None,
            late_accuracy=None,
            message=(
                f"Cold start: {samples}/{min_samples} history samples available. "
                "Risk model will train automatically after more completed tasks."
            ),
        )

        return get_risk_model_status()

    try:
        from joblib import dump
        from sklearn.linear_model import LogisticRegression
        from sklearn.metrics import accuracy_score
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler
    except Exception as exc:
        _update_status(
            trained=False,
            samples=samples,
            overtime_accuracy=None,
            late_accuracy=None,
            message=f"Risk model dependencies are missing or unavailable: {exc}",
        )

        return get_risk_model_status()

    X = [_feature_vector(row["features"]) for row in rows]
    y_overtime = [int(row["overtime_label"]) for row in rows]
    y_late = [int(row["late_label"]) for row in rows]

    overtime_model = None
    late_model = None
    overtime_accuracy = None
    late_accuracy = None

    if len(set(y_overtime)) >= 2:
        overtime_model = Pipeline([
            ("scaler", StandardScaler()),
            ("classifier", LogisticRegression(max_iter=1000)),
        ])
        overtime_model.fit(X, y_overtime)
        overtime_predictions = overtime_model.predict(X)
        overtime_accuracy = round(float(accuracy_score(y_overtime, overtime_predictions)), 3)

    if len(set(y_late)) >= 2:
        late_model = Pipeline([
            ("scaler", StandardScaler()),
            ("classifier", LogisticRegression(max_iter=1000)),
        ])
        late_model.fit(X, y_late)
        late_predictions = late_model.predict(X)
        late_accuracy = round(float(accuracy_score(y_late, late_predictions)), 3)

    if overtime_model is None or late_model is None:
        _update_status(
            trained=False,
            samples=samples,
            overtime_accuracy=overtime_accuracy,
            late_accuracy=late_accuracy,
            message=(
                "Not enough class variety to train both risk models yet. "
                "The system needs examples with both successful and risky outcomes."
            ),
        )

        return get_risk_model_status()

    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    dump({
        "model_name": MODEL_NAME,
        "feature_names": FEATURE_NAMES,
        "trained_at": datetime.now().isoformat(timespec="seconds"),
        "samples": samples,
        "overtime_model": overtime_model,
        "late_model": late_model,
        "overtime_accuracy": overtime_accuracy,
        "late_accuracy": late_accuracy,
    }, MODEL_PATH)

    _update_status(
        trained=True,
        samples=samples,
        overtime_accuracy=overtime_accuracy,
        late_accuracy=late_accuracy,
        message="Risk models trained successfully from task_history.",
    )

    return get_risk_model_status()


def predict_risk_with_model(
    planned_duration: int,
    priority: int,
    deadline: str,
) -> dict[str, Any] | None:
    status = get_risk_model_status()

    if not status.trained or status.samples < MIN_RISK_SAMPLES:
        status = retrain_risk_models()

    if not status.trained:
        return None

    if not MODEL_PATH.exists():
        status = retrain_risk_models()

        if not status.trained or not MODEL_PATH.exists():
            return None

    try:
        from joblib import load
    except Exception:
        return None

    payload = load(MODEL_PATH)

    overtime_model = payload.get("overtime_model")
    late_model = payload.get("late_model")

    if overtime_model is None or late_model is None:
        return None

    features = calculate_risk_features(
        planned_duration=planned_duration,
        priority=priority,
        deadline=deadline,
    )

    X = [_feature_vector(features)]

    overtime_prob = float(overtime_model.predict_proba(X)[0][1])
    late_prob = float(late_model.predict_proba(X)[0][1])

    return {
        "prediction_source": "risk_ml_model",
        "trained": True,
        "model_name": MODEL_NAME,
        "samples": status.samples,
        "features": features,
        "overtime_prob": round(overtime_prob, 2),
        "late_prob": round(late_prob, 2),
        "overtime_risk": _risk_bucket(overtime_prob),
        "late_risk": _risk_bucket(late_prob),
    }