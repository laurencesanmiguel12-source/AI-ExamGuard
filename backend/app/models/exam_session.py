from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

# Every terminal status submit_exam can leave a session in - not just "SUBMITTED" literally.
# FLAGGED_RETAKE/RETAKE_GRANTED/RETAKE_DENIED are still a real, scored, completed attempt (risk
# flagging is a separate axis from the academic result - see ExamSessionService.submit_exam), so
# anywhere that means "this student actually finished and got graded" should check this set, not
# just the "SUBMITTED" literal (report_service.py's stats, exam_content.py's answer-key reveal).
GRADED_STATUSES = {"SUBMITTED", "FLAGGED_RETAKE", "RETAKE_GRANTED", "RETAKE_DENIED"}


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

    # Head-down duration tracking (see face_service.py's head-pose estimate). Face-check polls
    # arrive every 5s and can't tell duration from a single snapshot on their own, so this state
    # has to be persisted rather than kept in-memory - an in-memory timer would silently reset on
    # a backend restart mid-exam. head_down_since is null whenever the student isn't currently
    # in a head-down streak; head_down_consecutive_count is the number of consecutive down polls
    # observed in the current streak (0 when not in one).
    head_down_since: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    head_down_consecutive_count: Mapped[int] = mapped_column(
        Integer,
        default=0
    )
    # Consecutive non-down polls since the last down poll, within the current streak. Exists
    # because an empirical simulation against real timestamped capture data (2026-07-31, see the
    # gaze-monitoring feasibility memory) found the streak resetting on ANY single miss made the
    # feature never fire at all, even during genuine 28-43s sustained phone-use episodes - a
    # single noisy poll where pitch happened to read above threshold discarded all accumulated
    # progress. HEAD_DOWN_MISS_TOLERANCE polls are now forgiven before the streak actually resets.
    head_down_miss_streak: Mapped[int] = mapped_column(
        Integer,
        default=0
    )
    # True once a PROLONGED_HEAD_DOWN violation has been logged for the *current* streak, so
    # verify() logs exactly one violation per streak instead of re-firing on every poll while
    # the student stays down. Reset to False the moment the streak breaks (see
    # face_service.py's _track_head_down).
    head_down_violation_logged: Mapped[bool] = mapped_column(
        Boolean,
        default=False
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
