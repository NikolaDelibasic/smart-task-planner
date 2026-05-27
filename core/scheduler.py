from datetime import datetime

from core.priority import priority_sort_value


def parse_deadline(deadline: str) -> datetime:
    """
    Supports:
    - YYYY-MM-DD
    - YYYY-MM-DD HH:MM
    """
    deadline = str(deadline).strip()

    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(deadline, fmt)
        except ValueError:
            pass

    raise ValueError("Deadline must be in format YYYY-MM-DD or YYYY-MM-DD HH:MM")


def suggest_order(tasks):
    """
    Active tasks sorted by:
    1. priority ascending: P1 before P2 before P3 before P4 before P5
    2. earliest deadline first
    3. shorter duration first
    4. title alphabetical
    """
    pending = [t for t in tasks if t["status"] != "completed"]

    def key(t):
        deadline_dt = parse_deadline(t["deadline"])

        return (
            priority_sort_value(t["priority"]),
            deadline_dt,
            int(t["duration"]),
            str(t["title"]).lower(),
        )

    return sorted(pending, key=key)