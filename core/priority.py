PRIORITY_MIN = 1
PRIORITY_MAX = 5
DEFAULT_PRIORITY = 3


PRIORITY_LABELS = {
    1: "P1 - Critical",
    2: "P2 - High",
    3: "P3 - Normal",
    4: "P4 - Low",
    5: "P5 - Optional",
}


PRIORITY_SHORT_LABELS = {
    1: "P1",
    2: "P2",
    3: "P3",
    4: "P4",
    5: "P5",
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
    P1 = most important
    P5 = least important

    AI score:
    P1 -> 5
    P2 -> 4
    P3 -> 3
    P4 -> 2
    P5 -> 1
    """
    priority = normalize_priority(value)
    return 6 - priority


def priority_sort_value(value) -> int:
    """
    Lower number means higher priority.

    P1 should be sorted before P2, P3, P4 and P5.
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