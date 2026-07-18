from sqlalchemy import Boolean, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Choice(Base, TimestampMixin):
    __tablename__ = "choices"

    id: Mapped[int] = mapped_column(primary_key=True)

    choice_text: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    is_correct: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )

    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id")
    )

    question = relationship(
        "Question",
        back_populates="choices"
    )