from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Violation(Base, TimestampMixin):
    __tablename__ = "violations"

    id: Mapped[int] = mapped_column(primary_key=True)

    exam_session_id: Mapped[int] = mapped_column(
        ForeignKey("exam_sessions.id")
    )

    event_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False
    )

    detail: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    exam_session = relationship(
        "ExamSession",
        back_populates="violations"
    )
