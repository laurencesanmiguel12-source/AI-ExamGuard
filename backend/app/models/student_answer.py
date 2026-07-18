from sqlalchemy import Boolean, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class StudentAnswer(Base, TimestampMixin):
    __tablename__ = "student_answers"

    id: Mapped[int] = mapped_column(primary_key=True)

    exam_session_id: Mapped[int] = mapped_column(
        ForeignKey("exam_sessions.id")
    )

    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id")
    )

    choice_id: Mapped[int | None] = mapped_column(
        ForeignKey("choices.id"),
        nullable=True
    )

    answer_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    is_correct: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )

    points_awarded: Mapped[int] = mapped_column(
        Integer,
        default=0
    )

    exam_session = relationship(
        "ExamSession",
        back_populates="answers"
    )

    question = relationship(
        "Question"
    )

    choice = relationship(
        "Choice"
    )