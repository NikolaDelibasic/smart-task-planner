from core.risk import assess_risk

WORKDAY_MINUTES = 8 * 60  # 09:00–17:00
SAFE_UTILIZATION = 0.85


def analyze_workload(tasks):
    active_tasks = [t for t in tasks if t["status"] != "completed"]

    total_minutes = sum(int(t["duration"]) for t in active_tasks)
    active_count = len(active_tasks)

    risk_count = 0
    urgent_count = 0

    for t in active_tasks:
        try:
            risk = assess_risk(
                priority=int(t["priority"]),
                planned=int(t["duration"]),
                deadline=str(t["deadline"]),
            )

            if risk.late_risk == "high" or risk.overtime_risk == "high":
                risk_count += 1
        except Exception:
            pass

        if t.get("is_overdue") or t.get("is_due_today") or t.get("is_due_soon"):
            urgent_count += 1

    utilization = round((total_minutes / WORKDAY_MINUTES) * 100, 1) if WORKDAY_MINUTES > 0 else 0.0

    warnings = []

    if total_minutes > WORKDAY_MINUTES * SAFE_UTILIZATION:
        warnings.append(
            f"Your active workload is {total_minutes} minutes, which is high compared to a standard workday capacity."
        )

    if active_count >= 8:
        warnings.append(
            "You currently have a large number of active tasks, which may reduce scheduling flexibility."
        )

    if urgent_count >= 3:
        warnings.append(
            "Several tasks are due today, overdue, or due very soon, which increases deadline pressure."
        )

    if risk_count >= 2:
        warnings.append(
            "Multiple active tasks currently show elevated execution or delay risk."
        )

    level = "none"
    if len(warnings) >= 3:
        level = "high"
    elif len(warnings) >= 1:
        level = "medium"

    return {
        "level": level,
        "utilization": utilization,
        "active_count": active_count,
        "total_minutes": total_minutes,
        "urgent_count": urgent_count,
        "risk_count": risk_count,
        "warnings": warnings[:3],
    }