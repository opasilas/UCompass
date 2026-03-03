from __future__ import annotations

from datetime import date, datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash

from models import db, Task, Student
from services import DashboardService

dashboard_bp = Blueprint("dashboard", __name__, template_folder="templates")
resources_bp = Blueprint("resources", __name__, template_folder="templates")
tasks_bp = Blueprint("tasks", __name__, template_folder="templates")
admin_bp = Blueprint("admin", __name__)

service = DashboardService()


def _parse_week_start(value: str | None) -> date:
    """
    Accept YYYY-MM-DD. If missing/invalid, default to current week's Monday.
    """
    today = date.today()
    monday = today - timedelta(days=today.weekday())

    if not value:
        return monday
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d").date()
        # normalize to Monday of that week
        return parsed - timedelta(days=parsed.weekday())
    except ValueError:
        return monday


from datetime import timedelta  # keep import near usage to avoid clutter



@admin_bp.post("/admin/students")
def create_student():
    data = request.get_json() or {}
    s = Student(
        name=data["name"],
        email=data["email"],
        course=data.get("course")
    )
    db.session.add(s)
    db.session.commit()
    return {"id": s.id, "name": s.name, "email": s.email}, 201


@dashboard_bp.get("/students/<int:student_id>/dashboard")
def student_dashboard(student_id: int):
    # StudentDashboardView
    week_start = _parse_week_start(request.args.get("week_start"))
    load_result = service.calculateWeeklyLoad(student_id=student_id, week_start=week_start)
    tasks = service.listStudentTasksInWeek(student_id=student_id, week_start=week_start)
    student = service.getStudent(student_id)

    # Alert logic: show banner / message when exceeded
    if load_result.exceeded:
        flash(
            f"Weekly load is {load_result.weekly_load:.1f} (threshold {load_result.threshold:.1f}). Consider reducing workload.",
            "warning",
        )

    return render_template(
        "student_dashboard.html",
        student=student,
        week=load_result,
        tasks=tasks,
    )


@dashboard_bp.get("/students/<int:student_id>/alert")
def alert_view(student_id: int):
    # AlertView (dedicated page)
    week_start = _parse_week_start(request.args.get("week_start"))
    load_result = service.calculateWeeklyLoad(student_id=student_id, week_start=week_start)
    student = service.getStudent(student_id)

    return render_template(
        "alert.html",
        student=student,
        week=load_result,
    )


@resources_bp.get("/resources")
def list_resources():
    # ResourceLibraryView (or similar)
    resources = service.fetchAllResources()
    return render_template("resources.html", resources=resources)


@tasks_bp.post("/tasks/<int:task_id>/progress")
def update_task_progress(task_id: int):
    """
    Example endpoint to update progress:
    - appends notes
    - logs effort
    """
    task = db.session.get(Task, task_id)
    if not task:
        flash("Task not found", "error")
        return redirect(request.referrer or url_for("resources.list_resources"))

    note = request.form.get("note", "")
    effort_spent = float(request.form.get("effort_spent", "0") or 0)
    progress = request.form.get("progress_percent")
    new_progress_percent = int(progress) if progress not in (None, "",) else None

    try:
        task.updateProgress(note=note, effort_spent=effort_spent, new_progress_percent=new_progress_percent)
        db.session.commit()
        flash("Progress updated.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Failed to update progress: {e}", "error")

    return redirect(request.referrer or url_for("dashboard.student_dashboard", student_id=task.student_id))


def register_blueprints(app):
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(resources_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(admin_bp)


    # this is a test change