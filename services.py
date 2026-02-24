from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Iterable

from sqlalchemy import select, func

from models import db, Student, Task, Resource


@dataclass(frozen=True)
class WeeklyLoadResult:
    student_id: int
    week_start: date
    week_end: date
    weekly_load: float
    threshold: float
    exceeded: bool


class DashboardService:
    """
    This acts like the DashboardController in a Controller-Service-Model pattern:
    - Routes/Controllers call into this service
    - Service queries DB and applies business rules
    """

    THRESHOLD: float = 5.0  # hardcoded per requirements

    @staticmethod
    def _week_bounds(week_start: date) -> tuple[date, date]:
        # inclusive start, inclusive end (7 days)
        week_end = week_start + timedelta(days=6)
        return week_start, week_end

    def calculateWeeklyLoad(self, *, student_id: int, week_start: date) -> WeeklyLoadResult:
        """
        Sum estimatedEffort for tasks within [week_start, week_start+6].
        """
        week_start, week_end = self._week_bounds(week_start)

        stmt = (
            select(func.coalesce(func.sum(Task.estimated_effort), 0.0))
            .where(Task.student_id == student_id)
            .where(Task.scheduled_date >= week_start)
            .where(Task.scheduled_date <= week_end)
        )
        weekly_load = float(db.session.execute(stmt).scalar_one())

        exceeded = self.checkThreshold(weekly_load)
        return WeeklyLoadResult(
            student_id=student_id,
            week_start=week_start,
            week_end=week_end,
            weekly_load=weekly_load,
            threshold=self.THRESHOLD,
            exceeded=exceeded,
        )

    def checkThreshold(self, weekly_load: float) -> bool:
        """
        Compare weekly load against threshold=5.
        """
        return weekly_load > self.THRESHOLD

    def fetchAllResources(self) -> list[Resource]:
        """
        Retrieve all available resources (for students to browse).
        """
        stmt = select(Resource).order_by(Resource.created_at.desc())
        return list(db.session.scalars(stmt).all())

    def getStudent(self, student_id: int) -> Student:
        student = db.session.get(Student, student_id)
        if not student:
            raise LookupError(f"Student {student_id} not found")
        return student

    def listStudentTasksInWeek(self, *, student_id: int, week_start: date) -> list[Task]:
        week_start, week_end = self._week_bounds(week_start)
        stmt = (
            select(Task)
            .where(Task.student_id == student_id)
            .where(Task.scheduled_date >= week_start)
            .where(Task.scheduled_date <= week_end)
            .order_by(Task.scheduled_date.asc(), Task.created_at.asc())
        )
        return list(db.session.scalars(stmt).all())