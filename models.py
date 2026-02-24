from __future__ import annotations

from datetime import datetime, date
from typing import Optional

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import CheckConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_type: Mapped[str] = mapped_column(db.String(50), nullable=False)  # discriminator

    name: Mapped[str] = mapped_column(db.String(120), nullable=False)
    email: Mapped[str] = mapped_column(db.String(255), unique=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)

    __mapper_args__ = {
        "polymorphic_on": user_type,
        "polymorphic_identity": "user",
    }

    def __repr__(self) -> str:
        return f"<User id={self.id} type={self.user_type} email={self.email}>"


class Student(User):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    course: Mapped[Optional[str]] = mapped_column(db.String(120), nullable=True)

    # One Student owns many Tasks
    tasks: Mapped[list["Task"]] = relationship(
        back_populates="student",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __mapper_args__ = {
        "polymorphic_identity": "student",
    }


class WellbeingOfficer(User):
    __tablename__ = "wellbeing_officers"

    id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    department: Mapped[Optional[str]] = mapped_column(db.String(120), nullable=True)

    # One WellbeingOfficer manages many Resources
    resources: Mapped[list["Resource"]] = relationship(
        back_populates="officer",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __mapper_args__ = {
        "polymorphic_identity": "wellbeing_officer",
    }


class Task(db.Model):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)

    title: Mapped[str] = mapped_column(db.String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(db.Text, nullable=True)

    # When the task is scheduled/expected (used for weekly load calculations)
    scheduled_date: Mapped[date] = mapped_column(db.Date, nullable=False)

    # "estimatedEffort" from the diagram (hard constraint to keep it sane)
    estimated_effort: Mapped[float] = mapped_column(db.Float, nullable=False, default=0.0)

    # progress tracking
    progress_percent: Mapped[int] = mapped_column(db.Integer, nullable=False, default=0)
    logged_effort: Mapped[float] = mapped_column(db.Float, nullable=False, default=0.0)

    # Free-form notes (append-only via updateProgress)
    notes: Mapped[str] = mapped_column(db.Text, nullable=False, default="")

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)
    student: Mapped["Student"] = relationship(back_populates="tasks")

    __table_args__ = (
        CheckConstraint("estimated_effort >= 0", name="ck_tasks_estimated_effort_nonneg"),
        CheckConstraint("logged_effort >= 0", name="ck_tasks_logged_effort_nonneg"),
        CheckConstraint("progress_percent >= 0 AND progress_percent <= 100", name="ck_tasks_progress_range"),
    )

    def updateProgress(self, *, note: str, effort_spent: float, new_progress_percent: Optional[int] = None) -> None:
        """
        Append a note (with timestamp) and log effort.
        This is kept on the model because it is domain behavior of Task.
        """
        if effort_spent < 0:
            raise ValueError("effort_spent must be >= 0")

        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        note_line = f"[{timestamp}] {note.strip()}\n" if note and note.strip() else f"[{timestamp}] (no note)\n"

        # Append notes
        self.notes = (self.notes or "") + note_line

        # Log effort
        self.logged_effort = float(self.logged_effort or 0.0) + float(effort_spent)

        # Update progress if provided
        if new_progress_percent is not None:
            if not (0 <= new_progress_percent <= 100):
                raise ValueError("new_progress_percent must be between 0 and 100")
            self.progress_percent = int(new_progress_percent)


class Resource(db.Model):
    __tablename__ = "resources"

    id: Mapped[int] = mapped_column(primary_key=True)

    title: Mapped[str] = mapped_column(db.String(200), nullable=False)
    category: Mapped[Optional[str]] = mapped_column(db.String(120), nullable=True)
    content: Mapped[Optional[str]] = mapped_column(db.Text, nullable=True)  # could be a link, description, etc.

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)

    officer_id: Mapped[int] = mapped_column(ForeignKey("wellbeing_officers.id"), nullable=False)
    officer: Mapped["WellbeingOfficer"] = relationship(back_populates="resources")