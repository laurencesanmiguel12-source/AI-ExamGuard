from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
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

    # Only populated for vision-based violation types (FACE_LOST, IDENTITY_MISMATCH,
    # PHONE_DETECTED, MULTIPLE_PEOPLE) - the webcam frame is already in hand at detection time for
    # those, unlike behavioral/extension events which have no visual counterpart. See
    # violation_service.py's log_violation for where this gets written.
    evidence_path: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    appeal_reason: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True
    )

    # None = no appeal filed. "PENDING" -> "UPHELD" (violation stands) or "OVERTURNED" (dismissed).
    appeal_status: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True
    )

    appeal_response: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True
    )

    # References users.id, not instructors.id - an admin (no linked Instructor row) can also review
    # an appeal, same as require_session_manage_access's admin-or-owning-instructor rule.
    appeal_reviewed_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True
    )

    appeal_reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    exam_session = relationship(
        "ExamSession",
        back_populates="violations"
    )

    @property
    def has_evidence(self) -> bool:
        return self.evidence_path is not None
