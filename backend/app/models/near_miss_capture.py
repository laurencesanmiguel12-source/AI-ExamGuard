from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class NearMissCapture(Base, TimestampMixin):
    """A frame the phone detector found plausible but did not act on.

    **Why this exists.** The training review queue can only ever show frames that produced a
    violation, so an admin reviewing it is looking exclusively at cases the model already got
    right - confirmed by measuring the batch approved on 2026-09-04, where all three phone frames
    were already detected at 0.80-0.88 confidence, comfortably above the 0.35 threshold. Frames
    the detector *missed* are the ones worth training on, and nothing was keeping them: the
    per-frame confidence was computed and then discarded.

    **Deliberately not a Violation row.** A near miss is not a violation - nothing happened to the
    student and nothing should appear on their record. Six services read Violation.event_type
    (risk scoring, reports, analytics, retention, the live monitor, the review queue), so adding a
    pseudo-violation type would mean auditing every one of them to exclude it, and any that was
    missed would silently inflate a student's risk or turn up in an instructor's report.

    **Privacy.** Same footing as the existing evidence store: object-detection frames only, never
    identity-linked ones, retained on the same 90-day clock, and only reaching training after an
    admin approves it - the same consent step violation evidence goes through. Capture is bounded
    per session (see object_detection_service) so a single exam cannot mass-retain frames of a
    student who did nothing wrong.
    """

    __tablename__ = "near_miss_captures"

    id: Mapped[int] = mapped_column(primary_key=True)

    exam_session_id: Mapped[int] = mapped_column(
        ForeignKey("exam_sessions.id"), index=True
    )

    # Which detector was unsure. Only "PHONE" is captured today; stored rather than assumed so
    # adding a second detector later does not need a migration.
    detector: Mapped[str] = mapped_column(String(30), nullable=False)

    # What the model actually scored this frame. The whole point of the record: it says how close
    # to the threshold the miss was, so the most informative frames can be reviewed first.
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    evidence_path: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Mirrors Violation's training-review columns so this flows through the same admin queue and
    # the same export discipline rather than inventing a second workflow.
    training_review_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="PENDING", server_default="PENDING"
    )

    training_exported_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    exam_session = relationship("ExamSession")
