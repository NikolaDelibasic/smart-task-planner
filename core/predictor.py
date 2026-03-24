from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Tuple

from core.database import get_connection


@dataclass
class Recommendation:
    recommended: int
    confidence: str
    details: Dict[str, float]


def _parse_deadline_date(deadline_str: str) -> date:
    return date.fromisoformat(str(deadline_str)[:10])


def _weekday_from_deadline(deadline_str: str) -> int:
    return _parse_deadline_date(deadline_str).weekday()


def _is_weekend_deadline(deadline_str: str) -> int:
    return 1 if _weekday_from_deadline(deadline_str) >= 5 else 0


def _days_to_deadline(deadline_str: str) -> int:
    today = date.today()
    deadline_date = _parse_deadline_date(deadline_str)
    return (deadline_date - today).days


def _get_training_rows(limit: int = 500):
    """
    Returns rows:
    (priority, planned_duration, deadline, actual_duration)
    """
    from core.database import get_connection

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT priority, planned_duration, deadline, actual_duration
            FROM task_history
            WHERE actual_duration IS NOT NULL
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))
        rows = cur.fetchall()

    out = []
    for row in rows:
        out.append((
            int(row["priority"]),
            int(row["planned_duration"]),
            str(row["deadline"]),
            int(row["actual_duration"])
        ))
    return out


def _solve_ridge_5x5(XtX: List[List[float]], Xty: List[float], lam: float = 1.0) -> List[float]:
    """
    Solves (XtX + lam*I) w = Xty for 5x5 matrix using Gaussian elimination.
    """
    n = 5
    A = [[XtX[r][c] + (lam if r == c else 0.0) for c in range(n)] for r in range(n)]
    b = [float(v) for v in Xty]

    for i in range(n):
        pivot_row = i
        for k in range(i + 1, n):
            if abs(A[k][i]) > abs(A[pivot_row][i]):
                pivot_row = k

        if pivot_row != i:
            A[i], A[pivot_row] = A[pivot_row], A[i]
            b[i], b[pivot_row] = b[pivot_row], b[i]

        pivot = A[i][i]
        if abs(pivot) < 1e-9:
            return [0.0, 1.0, 0.0, 0.0, 0.0]

        inv = 1.0 / pivot
        for j in range(i, n):
            A[i][j] *= inv
        b[i] *= inv

        for r in range(n):
            if r == i:
                continue
            factor = A[r][i]
            if abs(factor) < 1e-12:
                continue
            for c in range(i, n):
                A[r][c] -= factor * A[i][c]
            b[r] -= factor * b[i]

    return b


def _fit_model(rows: List[Tuple[int, int, str, int]]) -> Tuple[List[float], float]:
    """
    Features (5):
      x0 = 1 (bias)
      x1 = planned_duration
      x2 = priority
      x3 = weekend_deadline (0/1)
      x4 = days_to_deadline

    Target:
      y = actual_duration
    """
    n_features = 5
    XtX = [[0.0] * n_features for _ in range(n_features)]
    Xty = [0.0] * n_features
    Xs: List[List[float]] = []
    Ys: List[float] = []

    def feats(priority: int, planned: int, deadline: str) -> List[float]:
        return [
            1.0,
            float(planned),
            float(priority),
            float(_is_weekend_deadline(deadline)),
            float(_days_to_deadline(deadline))
        ]

    for priority, planned, deadline, actual in rows:
        x = feats(priority, planned, deadline)
        y = float(actual)

        Xs.append(x)
        Ys.append(y)

        for i in range(n_features):
            Xty[i] += x[i] * y
            for j in range(n_features):
                XtX[i][j] += x[i] * x[j]

    w = _solve_ridge_5x5(XtX, Xty, lam=5.0)

    abs_err_sum = 0.0
    for x, y in zip(Xs, Ys):
        pred = sum(w[i] * x[i] for i in range(n_features))
        abs_err_sum += abs(pred - y)

    mae = (abs_err_sum / len(rows)) if rows else 0.0
    return w, mae


def recommend_duration(priority: int, planned: int, deadline: str) -> Recommendation:
    priority = int(priority)
    planned = int(planned)
    deadline = str(deadline).strip()

    rows = _get_training_rows(limit=500)
    n = len(rows)

    if n < 8:
        buffer_map = {1: 0.05, 2: 0.12, 3: 0.20}
        buf = buffer_map.get(priority, 0.10)

        days_left = _days_to_deadline(deadline)
        if days_left <= 1:
            buf += 0.10
        elif days_left <= 3:
            buf += 0.05

        rec = int(round(planned * (1.0 + buf)))

        return Recommendation(
            recommended=max(5, rec),
            confidence="low",
            details={
                "rule_buffer_pct": round(buf * 100.0, 1),
                "samples": float(n),
                "days_to_deadline": float(days_left)
            }
        )

    w, mae = _fit_model(rows)

    x = [
        1.0,
        float(planned),
        float(priority),
        float(_is_weekend_deadline(deadline)),
        float(_days_to_deadline(deadline))
    ]
    pred = sum(w[i] * x[i] for i in range(5))

    rec = int(round(max(5.0, pred)))

    if mae <= 8:
        conf = "high"
    elif mae <= 15:
        conf = "medium"
    else:
        conf = "low"

    return Recommendation(
        recommended=rec,
        confidence=conf,
        details={
            "samples": float(n),
            "mae_min": round(mae, 1),
            "w_bias": round(w[0], 4),
            "w_planned": round(w[1], 4),
            "w_priority": round(w[2], 4),
            "w_weekend": round(w[3], 4),
            "w_days_to_deadline": round(w[4], 4),
            "weekend_deadline": float(_is_weekend_deadline(deadline)),
            "days_to_deadline": float(_days_to_deadline(deadline)),
        }
    )