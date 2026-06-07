PRIORITY_MIN = 1
PRIORITY_MAX = 5
DEFAULT_PRIORITY = 3


PRIORITY_LABELS = {
    1: "Critical",
    2: "High",
    3: "Normal",
    4: "Low",
    5: "Optional",
}


PRIORITY_SHORT_LABELS = {
    1: "Critical",
    2: "High",
    3: "Normal",
    4: "Low",
    5: "Optional",
}


PRIORITY_BADGES = {
    1: "danger",
    2: "warning",
    3: "primary",
    4: "secondary",
    5: "light",
}


def normalize_priority(value, default: int = DEFAULT_PRIORITY) -> int:
    try:
        priority = int(value)
    except (TypeError, ValueError):
        return default

    if priority < PRIORITY_MIN:
        return PRIORITY_MIN

    if priority > PRIORITY_MAX:
        return PRIORITY_MAX

    return priority


def priority_label(value) -> str:
    priority = normalize_priority(value)
    return PRIORITY_LABELS.get(priority, PRIORITY_LABELS[DEFAULT_PRIORITY])


def priority_short_label(value) -> str:
    priority = normalize_priority(value)
    return PRIORITY_SHORT_LABELS.get(priority, PRIORITY_SHORT_LABELS[DEFAULT_PRIORITY])


def priority_badge(value) -> str:
    priority = normalize_priority(value)
    return PRIORITY_BADGES.get(priority, PRIORITY_BADGES[DEFAULT_PRIORITY])


def importance_score(value) -> int:
    """
    Converts user-facing priority into AI-friendly importance.

    User scale:
    1 = Critical
    5 = Optional

    AI score:
    Critical -> 5
    High -> 4
    Normal -> 3
    Low -> 2
    Optional -> 1
    """
    priority = normalize_priority(value)
    return 6 - priority


def priority_sort_value(value) -> int:
    """
    Lower number means higher priority.

    Critical should be sorted before High, Normal, Low and Optional.
    """
    return normalize_priority(value)


def priority_options():
    return [
        {
            "value": value,
            "label": label,
            "short_label": PRIORITY_SHORT_LABELS[value],
            "badge": PRIORITY_BADGES[value],
            "importance_score": importance_score(value),
        }
        for value, label in PRIORITY_LABELS.items()
    ]