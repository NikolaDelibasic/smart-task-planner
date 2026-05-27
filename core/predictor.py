from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.ml_model import (
    MIN_TRAINING_SAMPLES,
    calculate_duration_features,
    get_model_status,
    predict_duration_with_model,
)
from core.priority import normalize_priority


@dataclass
class Recommendation:
    recommended: int
    confidence: str
    details: dict[str, Any]


def _confidence_from_mae(mae: float | None) -> str:
    if mae is None:
        return "low"

    if mae <= 8:
        return "high"

    if mae <= 15:
        return "medium"

    return "low"


def _cold_start_prediction(priority: int, planned: int, deadline: str) -> Recommendation:
    priority = normalize_priority(priority)

    features = calculate_duration_features(
        planned_duration=planned,
        priority=priority,
        deadline=deadline,
    )

    buffer_map = {
        1: 0.25,
        2: 0.18,
        3: 0.12,
        4: 0.08,
        5: 0.05,
    }

    buffer = buffer_map.get(priority, 0.12)

    days_left = features["days_to_deadline"]

    if days_left <= 0:
        buffer += 0.15
    elif days_left <= 1:
        buffer += 0.10
    elif days_left <= 3:
        buffer += 0.05

    if features["weekend_deadline"] == 1:
        buffer += 0.05

    recommended = int(round(planned * (1.0 + buffer)))
    status = get_model_status()

    return Recommendation(
        recommended=max(5, recommended),
        confidence="low",
        details={
            "prediction_source": "cold_start_fallback",
            "model_trained": False,
            "model_name": status.model_name,
            "samples": status.samples,
            "min_samples": MIN_TRAINING_SAMPLES,
            "mae_min": status.mae,
            "rule_buffer_pct": round(buffer * 100.0, 1),
            "planned_duration": features["planned_duration"],
            "priority": features["priority"],
            "days_to_deadline": features["days_to_deadline"],
            "weekend_deadline": features["weekend_deadline"],
            "message": status.message,
        },
    )


def recommend_duration(priority: int, planned: int, deadline: str) -> Recommendation:
    priority = normalize_priority(priority)
    planned = int(planned)
    deadline = str(deadline).strip()

    if planned <= 0:
        return Recommendation(
            recommended=5,
            confidence="low",
            details={
                "prediction_source": "invalid_input_fallback",
                "message": "Planned duration must be greater than 0.",
            },
        )

    ml_prediction = predict_duration_with_model(
        planned_duration=planned,
        priority=priority,
        deadline=deadline,
    )

    if ml_prediction is None:
        return _cold_start_prediction(
            priority=priority,
            planned=planned,
            deadline=deadline,
        )

    mae = ml_prediction["mae"]

    return Recommendation(
        recommended=ml_prediction["recommended"],
        confidence=_confidence_from_mae(mae),
        details={
            "prediction_source": "ml_model",
            "model_trained": True,
            "model_name": ml_prediction["model_name"],
            "samples": ml_prediction["samples"],
            "min_samples": MIN_TRAINING_SAMPLES,
            "mae_min": mae,
            "planned_duration": ml_prediction["features"]["planned_duration"],
            "priority": ml_prediction["features"]["priority"],
            "days_to_deadline": ml_prediction["features"]["days_to_deadline"],
            "weekend_deadline": ml_prediction["features"]["weekend_deadline"],
            "updated_at": ml_prediction["updated_at"],
        },
    )