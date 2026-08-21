import os
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.course import Course
from app.models.exam import Exam
from app.models.exam_session import ExamSession
from app.models.subject import Subject
from app.models.violation import Violation
from app.services.audit_log_service import AuditLogService

# Conservative default: long enough to cover a realistic appeal/grade-dispute window, not
# indefinite storage of biometric evidence. Easily adjusted if the institution's policy differs -
# not exposed as an admin-configurable setting since this project has no settings table yet and
# a hardcoded, documented constant is more honest than a UI control that implies more flexibility
# than actually exists.
EVIDENCE_RETENTION_DAYS = 90


def _eligible_query(db: Session, school_id: int | None):
    cutoff = datetime.now(timezone.utc) - timedelta(days=EVIDENCE_RETENTION_DAYS)
    query = (
        db.query(Violation)
        # Scoped by school - previously system-wide, so School A's admin could preview/purge
        # School B's biometric evidence. school_id=None is the one legitimate exception - a
        # super admin previewing across every school at once - but see purge_expired_evidence's
        # own comment for why the actual delete never allows that.
        .join(ExamSession, Violation.exam_session_id == ExamSession.id)
        .join(Exam, ExamSession.exam_id == Exam.id)
        .join(Subject, Exam.subject_id == Subject.id)
        .join(Course, Subject.course_id == Course.id)
    )
    if school_id is not None:
        query = query.filter(Course.school_id == school_id)
    return (
        query
        .filter(Violation.evidence_path.isnot(None))
        .filter(Violation.created_at < cutoff)
        # A PENDING appeal still needs its evidence reviewed - never purge out from under an
        # unresolved due-process decision. Resolved appeals (UPHELD/OVERTURNED) and violations
        # that were never appealed at all are both safe to purge once past the retention window.
        # NULL-safe on purpose: plain `appeal_status != "PENDING"` evaluates to SQL NULL (not TRUE)
        # for never-appealed violations (appeal_status IS NULL), silently excluding them too -
        # confirmed by a real failing test case, not a hypothetical.
        .filter(or_(Violation.appeal_status.is_(None), Violation.appeal_status != "PENDING"))
        # Same shape for the training-review queue: an unreviewed (PENDING) candidate, or an
        # APPROVED one that export_reviewed_evidence.py hasn't copied out yet, still needs its
        # file on disk. REJECTED and already-exported APPROVED items are safe to purge on the
        # normal schedule - a copy already lives in the training set for the latter.
        .filter(
            or_(
                Violation.training_review_status.is_(None),
                Violation.training_review_status == "REJECTED",
                Violation.training_exported_at.isnot(None),
            )
        )
    )


class RetentionService:

    @staticmethod
    def preview_purge(db: Session, school_id: int | None):
        violations = _eligible_query(db, school_id).order_by(Violation.created_at).all()
        return {
            "retention_days": EVIDENCE_RETENTION_DAYS,
            "eligible_count": len(violations),
            "violations": [
                {
                    "id": v.id,
                    "event_type": v.event_type,
                    "created_at": v.created_at,
                    "appeal_status": v.appeal_status,
                }
                for v in violations
            ],
        }

    @staticmethod
    def purge_expired_evidence(db: Session, actor_user_id: int, school_id: int) -> int:
        # Deliberately not int | None like preview_purge/_eligible_query - actually deleting
        # files is not something a super admin should ever be able to trigger platform-wide by
        # omission. routes/retention.py enforces this: a super admin must pass an explicit
        # ?school_id= to purge at all, a regular admin's own school_id is always used regardless
        # of what they pass.
        violations = _eligible_query(db, school_id).all()

        purged = 0
        for v in violations:
            path = v.evidence_path
            if path and os.path.exists(path):
                os.remove(path)

            v.evidence_path = None
            purged += 1

            AuditLogService.log(
                actor_user_id, "PURGE_EVIDENCE", "violation", v.id, db,
                detail=f"event_type={v.event_type}, was created_at={v.created_at.isoformat()}"
            )

        db.commit()
        return purged
