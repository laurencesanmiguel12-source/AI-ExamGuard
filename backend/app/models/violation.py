from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Violation(Base, TimestampMixin):
    __tablename__ = "violations"

    id: Mapped[int] = mapped_column(primary_key=True)

    exam_session_id: Mapped[int] = mapped_column(
        ForeignKey("exam_sessions.id"), index=True
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

    # Question-context snapshot, currently only populated for PROLONGED_HEAD_DOWN. A denormalized
    # copy (not just question_id) so the record stays meaningful on its own - "this is a 500-word
    # essay question, 25s head-down is obviously normal" vs "this is one multiple-choice line" is
    # exactly the plausibility judgment a reviewer needs, and shouldn't depend on the live Question
    # row still matching what the student actually saw at flag time. This is a geometric proxy
    # signal, not a direct visual identification like PHONE_DETECTED, so there's no webcam frame to
    # fall back on - see evidence_path's comment above.
    question_id: Mapped[int | None] = mapped_column(
        ForeignKey("questions.id"),
        nullable=True
    )
    question_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )
    question_type: Mapped[str | None] = mapped_column(
        String(30),
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

    # Continuous-training review queue. None = not a training candidate (wrong event_type, or no
    # evidence). "PENDING" is set automatically at creation for object-detection evidence types
    # (see TRAINING_CANDIDATE_EVENT_TYPES in violation_service.py) - identity-linked types
    # (FACE_LOST, IDENTITY_MISMATCH) are deliberately excluded, since reusing biometric-identity
    # frames for training needs its own separate consent, not this disclosure. "APPROVED"/
    # "REJECTED" set by an admin via training_review_service.py. RetentionService protects
    # PENDING and not-yet-exported APPROVED evidence from the 90-day purge.
    training_review_status: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True
    )

    training_reviewed_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True
    )

    training_reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Set once export_reviewed_evidence.py has copied this evidence file into the training
    # dataset. Only then is the live copy safe to purge on the normal 90-day schedule.
    training_exported_at: Mapped[datetime | None] = mapped_column(
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
