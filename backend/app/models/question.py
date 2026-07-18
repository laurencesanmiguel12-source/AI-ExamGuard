from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Question(Base, TimestampMixin):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True)

    question_text: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    question_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False
    )

    points: Mapped[int] = mapped_column(
        Integer,
        default=1
    )

    order_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    exam_id: Mapped[int] = mapped_column(
        ForeignKey("exams.id")
    )

    exam = relationship(
        "Exam",
        back_populates="questions"
    )