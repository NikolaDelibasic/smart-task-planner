from calendar import monthrange
from datetime import date, datetime, timedelta


VALID_REPEAT_TYPES = {"none", "daily", "weekly", "monthly"}


def normalize_repeat_type(value):
    value = str(value or "none").strip().lower()

    if value not in VALID_REPEAT_TYPES:
        return "none"

    return value


def normalize_repeat_interval(value, default=1):
    try:
        interval = int(value)
    except (TypeError, ValueError):
        interval = default

    return max(1, min(interval, 365))


def parse_deadline_value(value):
    """
    Supports:
    - YYYY-MM-DD
    - YYYY-MM-DD HH:MM
    - YYYY-MM-DDTHH:MM
    """
    raw = str(value or "").strip()

    if not raw:
        return None, False

    try:
        if "T" in raw or " " in raw:
            normalized = raw.replace(" ", "T")
            return datetime.fromisoformat(normalized), True

        return date.fromisoformat(raw[:10]), False

    except ValueError:
        return None, False


def _add_months(value, months):
    if isinstance(value, datetime):
        year = value.year
        month = value.month
        day = value.day
        hour = value.hour
        minute = value.minute
        second = value.second
        microsecond = value.microsecond
    else:
        year = value.year
        month = value.month
        day = value.day
        hour = minute = second = microsecond = None

    month_index = month - 1 + months
    new_year = year + month_index // 12
    new_month = month_index % 12 + 1

    last_day = monthrange(new_year, new_month)[1]
    new_day = min(day, last_day)

    if isinstance(value, datetime):
        return datetime(
            new_year,
            new_month,
            new_day,
            hour,
            minute,
            second,
            microsecond,
        )

    return date(new_year, new_month, new_day)


def get_next_deadline(deadline, repeat_type, repeat_interval=1):
    repeat_type = normalize_repeat_type(repeat_type)
    repeat_interval = normalize_repeat_interval(repeat_interval)

    if repeat_type == "none":
        return None

    parsed, has_time = parse_deadline_value(deadline)

    if parsed is None:
        return None

    if repeat_type == "daily":
        next_value = parsed + timedelta(days=repeat_interval)

    elif repeat_type == "weekly":
        next_value = parsed + timedelta(weeks=repeat_interval)

    elif repeat_type == "monthly":
        next_value = _add_months(parsed, repeat_interval)

    else:
        return None

    if has_time and isinstance(next_value, datetime):
        return next_value.isoformat(timespec="minutes")

    if isinstance(next_value, datetime):
        return next_value.date().isoformat()

    return next_value.isoformat()


def recurrence_label(repeat_type, repeat_interval=1):
    repeat_type = normalize_repeat_type(repeat_type)
    repeat_interval = normalize_repeat_interval(repeat_interval)

    if repeat_type == "none":
        return ""

    if repeat_type == "daily":
        if repeat_interval == 1:
            return "Repeats daily"
        return f"Repeats every {repeat_interval} days"

    if repeat_type == "weekly":
        if repeat_interval == 1:
            return "Repeats weekly"
        return f"Repeats every {repeat_interval} weeks"

    if repeat_type == "monthly":
        if repeat_interval == 1:
            return "Repeats monthly"
        return f"Repeats every {repeat_interval} months"

    return ""