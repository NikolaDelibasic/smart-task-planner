from datetime import datetime


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
    tasks: iterable of sqlite3.Row objects
    Returns pending tasks sorted by:
    1. priority descending
    2. earliest deadline first
    3. shorter duration first
    4. title alphabetical
    """
    pending = [t for t in tasks if t["status"] != "completed"]

    def key(t):
        deadline_dt = parse_deadline(t["deadline"])
        return (
            -int(t["priority"]),
            deadline_dt,
            int(t["duration"]),
            str(t["title"]).lower()
        )

    return sorted(pending, key=key)