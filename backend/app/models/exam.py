from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship


from app.models.base import Base, TimestampMixin



class Exam(Base, TimestampMixin):
    __tablename__ = "exams"

    id: Mapped[int] = mapped_column(primary_key=True)

    title: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    duration_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    total_points: Mapped[int] = mapped_column(
        Integer,
        default=0
    )

    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True)
    )

    end_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True)
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )

    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subjects.id")
    )

    instructor_id: Mapped[int] = mapped_column(
        ForeignKey("instructors.id")
    )

    subject = relationship(
        "Subject",
        back_populates="exams"
    )

    instructor = relationship(
        "Instructor",
        back_populates="exams"
    )

    questions = relationship(
        "Question",
        back_populates="exam",
        cascade="all, delete-orphan"
    )