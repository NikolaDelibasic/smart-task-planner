from datetime import date, datetime, timedelta

from flask import Flask, jsonify, redirect, render_template, request, url_for

from core.auto_scheduler import generate_daily_plan
from core.database import init_db
from core.predictor import recommend_duration
from core.risk import assess_risk
from core.scheduler import suggest_order
from core.stats import get_basic_stats
from core.task_manager import (
    add_task,
    delete_task,
    get_active_tasks,
    get_all_tasks,
    get_completed_tasks,
    get_tasks_by_date_range,
    mark_completed,
)
from core.workload import analyze_workload

app = Flask(__name__)

init_db()

MAX_PLANNER_BLOCKS = 5


def _safe_parse_task_date(deadline_value: str):
    try:
        return date.fromisoformat(str(deadline_value)[:10])
    except Exception:
        return None


def _format_datetime_for_ui(value: str | None):
    if not value:
        return None

    try:
        dt = datetime.fromisoformat(str(value))
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(value)


def _parse_time_value(value: str):
    try:
        parts = str(value).strip().split(":")
        if len(parts) != 2:
            return None

        hour = int(parts[0])
        minute = int(parts[1])

        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            return None

        return hour, minute
    except Exception:
        return None


def _normalize_block_count(raw_value, default=1):
    try:
        count = int(raw_value)
    except (TypeError, ValueError):
        count = default

    return max(1, min(MAX_PLANNER_BLOCKS, count))


def _collect_time_blocks_from_request(req_args, block_count: int) -> str:
    blocks = []

    for i in range(1, block_count + 1):
        start_val = req_args.get(f"block_{i}_start", "").strip()
        end_val = req_args.get(f"block_{i}_end", "").strip()

        if not start_val or not end_val:
            continue

        start_parsed = _parse_time_value(start_val)
        end_parsed = _parse_time_value(end_val)

        if not start_parsed or not end_parsed:
            continue

        start_minutes = start_parsed[0] * 60 + start_parsed[1]
        end_minutes = end_parsed[0] * 60 + end_parsed[1]

        if end_minutes <= start_minutes:
            continue

        blocks.append(f"{start_val}-{end_val}")

    return ", ".join(blocks)


def _extract_block_fields_from_time_blocks(time_blocks: str, block_count: int):
    values = {}

    for i in range(1, MAX_PLANNER_BLOCKS + 1):
        values[f"block_{i}_start"] = ""
        values[f"block_{i}_end"] = ""

    chunks = [chunk.strip() for chunk in str(time_blocks or "").split(",") if chunk.strip()]

    parsed_pairs = []
    for chunk in chunks:
        if "-" not in chunk:
            continue
        left, right = chunk.split("-", 1)
        left = left.strip()
        right = right.strip()

        if _parse_time_value(left) and _parse_time_value(right):
            parsed_pairs.append((left, right))

    effective_count = max(block_count, len(parsed_pairs))
    effective_count = max(1, min(MAX_PLANNER_BLOCKS, effective_count))

    for idx, pair in enumerate(parsed_pairs[:MAX_PLANNER_BLOCKS], start=1):
        values[f"block_{idx}_start"] = pair[0]
        values[f"block_{idx}_end"] = pair[1]

    return effective_count, values


def _decorate_tasks(tasks):
    today = date.today()
    decorated = []

    for task in tasks:
        task_dict = dict(task)

        deadline_date = _safe_parse_task_date(task_dict.get("deadline", ""))
        status = task_dict.get("status", "pending")

        task_dict["is_overdue"] = False
        task_dict["is_due_today"] = False
        task_dict["is_due_soon"] = False
        task_dict["days_left"] = None
        task_dict["risk"] = None
        task_dict["created_at_display"] = _format_datetime_for_ui(task_dict.get("created_at"))
        task_dict["completed_at_display"] = _format_datetime_for_ui(task_dict.get("completed_at"))

        if deadline_date:
            days_left = (deadline_date - today).days
            task_dict["days_left"] = days_left

            if status != "completed":
                task_dict["is_overdue"] = days_left < 0
                task_dict["is_due_today"] = days_left == 0
                task_dict["is_due_soon"] = 0 < days_left <= 2

        if status != "completed":
            try:
                risk = assess_risk(
                    priority=int(task_dict["priority"]),
                    planned=int(task_dict["duration"]),
                    deadline=str(task_dict["deadline"]),
                )
                task_dict["risk"] = {
                    "overtime_risk": risk.overtime_risk,
                    "late_risk": risk.late_risk,
                }
            except Exception:
                task_dict["risk"] = None

        decorated.append(task_dict)

    return decorated


def _current_workload_payload():
    tasks = _decorate_tasks(get_all_tasks())
    workload = analyze_workload(tasks)
    return {
        "level": workload["level"],
        "utilization": workload["utilization"],
        "active_count": workload["active_count"],
        "total_minutes": workload["total_minutes"],
        "urgent_count": workload["urgent_count"],
        "risk_count": workload["risk_count"],
        "warnings": workload["warnings"],
    }


@app.context_processor
def inject_globals():
    return {
        "app_name": "Smart Task Planner",
        "current_year": datetime.now().year,
    }


@app.route("/")
def home():
    tasks = _decorate_tasks(get_all_tasks())
    workload = analyze_workload(tasks)
    return render_template(
        "index.html",
        tasks=tasks,
        title="All Tasks",
        active_page="all",
        workload=workload,
    )


@app.route("/add", methods=["POST"])
def add():
    title = request.form.get("title", "").strip()
    priority = request.form.get("priority", "1").strip()
    deadline = request.form.get("deadline", "").strip()
    duration = request.form.get("duration", "0").strip()
    used_recommendation = request.form.get("used_recommendation", "0").strip()

    try:
        priority = int(priority)
        duration = int(duration)
        used_recommendation = int(used_recommendation)
    except ValueError:
        return redirect(url_for("home"))

    if not title or not deadline or duration <= 0:
        return redirect(url_for("home"))

    add_task(title, priority, deadline, duration, used_recommendation=used_recommendation)
    return redirect(url_for("home"))


@app.route("/delete/<int:task_id>", methods=["POST"])
def delete(task_id):
    delete_task(task_id)
    return redirect(url_for("home"))


@app.route("/api/delete/<int:task_id>", methods=["POST"])
def api_delete(task_id):
    try:
        delete_task(task_id)
        return jsonify({
            "ok": True,
            "task_id": task_id,
            "workload": _current_workload_payload(),
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/complete/<int:task_id>")
def complete_form(task_id):
    return render_template("complete.html", task_id=task_id, active_page="all")


@app.route("/done/<int:task_id>", methods=["POST"])
def done(task_id):
    actual_duration = request.form.get("actual_duration", "0").strip()

    try:
        actual_duration = int(actual_duration)
    except ValueError:
        return redirect(url_for("complete_form", task_id=task_id))

    if actual_duration <= 0:
        return redirect(url_for("complete_form", task_id=task_id))

    mark_completed(task_id, actual_duration)
    return redirect(url_for("home"))


@app.route("/api/complete/<int:task_id>", methods=["POST"])
def api_complete(task_id):
    try:
        payload = request.get_json(silent=True) or {}
        actual_duration = payload.get("actual_duration")

        if actual_duration is None:
            actual_duration = request.form.get("actual_duration", "0")

        actual_duration = int(actual_duration)

        if actual_duration <= 0:
            return jsonify({"ok": False, "error": "Actual duration must be greater than 0."}), 400

        mark_completed(task_id, actual_duration)

        return jsonify({
            "ok": True,
            "task_id": task_id,
            "actual_duration": actual_duration,
            "workload": _current_workload_payload(),
        })
    except ValueError:
        return jsonify({"ok": False, "error": "Invalid actual duration."}), 400
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/workload")
def api_workload():
    return jsonify({
        "ok": True,
        "workload": _current_workload_payload(),
    })


@app.route("/active")
def active():
    tasks = _decorate_tasks(get_active_tasks())
    workload = analyze_workload(tasks)
    return render_template(
        "index.html",
        tasks=tasks,
        title="Active Tasks",
        active_page="active",
        workload=workload,
    )


@app.route("/done")
def done_view():
    tasks = _decorate_tasks(get_completed_tasks())
    workload = analyze_workload(tasks)
    return render_template(
        "index.html",
        tasks=tasks,
        title="Completed Tasks",
        active_page="done",
        workload=workload,
    )


@app.route("/view")
def view():
    mode = request.args.get("mode")
    date_param = request.args.get("date")
    today = date.today()

    if date_param:
        try:
            selected = date.fromisoformat(date_param)
        except ValueError:
            return redirect(url_for("home"))

        start = selected.isoformat()
        end = (selected + timedelta(days=1)).isoformat()

        tasks = _decorate_tasks(get_tasks_by_date_range(start, end))
        return render_template(
            "index.html",
            tasks=tasks,
            title=f"Tasks for {start}",
            active_page="view",
            workload=analyze_workload(tasks),
        )

    if mode == "today":
        start = today
        end = today + timedelta(days=1)
        title = "Today"
    elif mode == "week":
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=7)
        title = "This Week"
    elif mode == "month":
        start = today.replace(day=1)
        if start.month == 12:
            end = start.replace(year=start.year + 1, month=1)
        else:
            end = start.replace(month=start.month + 1)
        title = "This Month"
    elif mode == "year":
        start = today.replace(month=1, day=1)
        end = start.replace(year=start.year + 1)
        title = "This Year"
    else:
        return redirect(url_for("home"))

    tasks = _decorate_tasks(get_tasks_by_date_range(start.isoformat(), end.isoformat()))
    return render_template(
        "index.html",
        tasks=tasks,
        title=title,
        active_page="view",
        workload=analyze_workload(tasks),
    )


@app.route("/suggest")
def suggest():
    tasks = suggest_order(get_all_tasks())
    tasks = _decorate_tasks(tasks)
    return render_template(
        "suggest.html",
        tasks=tasks,
        active_page="suggest",
    )


@app.route("/stats")
def stats():
    data = get_basic_stats()
    return render_template(
        "stats.html",
        stats=data,
        active_page="stats",
    )


@app.route("/planner")
def planner():
    tasks = _decorate_tasks(get_active_tasks())
    workload = analyze_workload(tasks)

    start_time = request.args.get("start_time", "09:00").strip()

    try:
        available_minutes = int(request.args.get("available_minutes", "480"))
    except ValueError:
        available_minutes = 480

    try:
        break_minutes = int(request.args.get("break_minutes", "10"))
    except ValueError:
        break_minutes = 10

    try:
        min_split_minutes = int(request.args.get("min_split_minutes", "15"))
    except ValueError:
        min_split_minutes = 15

    use_predicted_raw = request.args.get("use_predicted", "1")
    use_predicted = use_predicted_raw == "1"

    allow_split_raw = request.args.get("allow_split", "1")
    allow_split = allow_split_raw == "1"

    block_count = _normalize_block_count(request.args.get("block_count", "1"), default=1)
    time_blocks = _collect_time_blocks_from_request(request.args, block_count)

    schedule, unscheduled, planner_meta = generate_daily_plan(
        tasks,
        use_predicted=use_predicted,
        start_time=start_time,
        available_minutes=available_minutes,
        break_minutes=break_minutes,
        time_blocks=time_blocks,
        allow_split=allow_split,
        min_split_minutes=min_split_minutes,
    )

    effective_block_count, block_fields = _extract_block_fields_from_time_blocks(
        planner_meta.get("time_blocks", ""),
        block_count,
    )

    return render_template(
        "planner.html",
        schedule=schedule,
        unscheduled=unscheduled,
        active_page="planner",
        workload=workload,
        planner_meta=planner_meta,
        planner_block_count=effective_block_count,
        planner_block_fields=block_fields,
        max_planner_blocks=MAX_PLANNER_BLOCKS,
    )


@app.route("/api/recommend")
def api_recommend():
    try:
        priority = int(request.args.get("priority", "2"))
        planned = int(request.args.get("planned", "0"))
        deadline = request.args.get("deadline", "").strip()

        if planned <= 0 or not deadline:
            return jsonify({"ok": False, "error": "Missing planned or deadline"}), 400

        rec = recommend_duration(priority=priority, planned=planned, deadline=deadline)

        return jsonify({
            "ok": True,
            "recommended": rec.recommended,
            "confidence": rec.confidence,
            "details": rec.details,
        })
    except ValueError:
        return jsonify({"ok": False, "error": "Invalid input"}), 400
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/risk")
def api_risk():
    try:
        priority = int(request.args.get("priority", "2"))
        planned = int(request.args.get("planned", "0"))
        deadline = request.args.get("deadline", "").strip()

        if planned <= 0 or not deadline:
            return jsonify({"ok": False, "error": "Missing planned or deadline"}), 400

        r = assess_risk(priority=priority, planned=planned, deadline=deadline)

        return jsonify({
            "ok": True,
            "overtime_risk": r.overtime_risk,
            "late_risk": r.late_risk,
            "overtime_prob": r.overtime_prob,
            "late_prob": r.late_prob,
            "reasons": r.reasons,
        })
    except ValueError:
        return jsonify({"ok": False, "error": "Invalid input"}), 400
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)