from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class ExamRoster(Base, TimestampMixin):
    __tablename__ = "exam_rosters"
    __table_args__ = (
        UniqueConstraint("exam_id", "student_id", name="uq_exam_roster_exam_student"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    exam_id: Mapped[int] = mapped_column(
        ForeignKey("exams.id")
    )

    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id")
    )

    exam = relationship(
        "Exam",
        back_populates="roster_entries"
    )

    student = relationship(
        "Student",
        back_populates="roster_entries"
    )
