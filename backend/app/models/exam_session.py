from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class ExamSession(Base, TimestampMixin):
    __tablename__ = "exam_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)

    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id")
    )

    exam_id: Mapped[int] = mapped_column(
        ForeignKey("exams.id")
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True)
    )

    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    score: Mapped[int] = mapped_column(
        Integer,
        default=0
    )
    percentage: Mapped[float] = mapped_column(
        default=0
    )

    passed: Mapped[bool] = mapped_column(
        default=False
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default="IN_PROGRESS"
    )

    student = relationship(
        "Student",
        back_populates="exam_sessions"
    )

    exam = relationship(
        "Exam",
        back_populates="exam_sessions"
    )
    answers = relationship(
        "StudentAnswer",
        back_populates="exam_session",
        cascade="all, delete-orphan"
    )
    violations = relationship(
        "Violation",
        back_populates="exam_session",
        cascade="all, delete-orphan"
    )
