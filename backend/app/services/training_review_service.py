from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.course import Course
from app.models.exam import Exam
from app.models.exam_session import ExamSession
from app.models.subject import Subject
from app.models.violation import Violation
from app.services.audit_log_service import AuditLogService

REVIEW_DECISIONS = {"APPROVED", "REJECTED"}


def _school_scoped_query(db: Session, school_id: int | None):
    query = (
        db.query(Violation)
        # Scoped by school, same pattern as retention_service - an admin only ever reviews or
        # exports their own school's evidence for training use. school_id=None is the super
        # admin exception, matching every other list-style query in this codebase.
        .join(ExamSession, Violation.exam_session_id == ExamSession.id)
        .join(Exam, ExamSession.exam_id == Exam.id)
        .join(Subject, Exam.subject_id == Subject.id)
        .join(Course, Subject.course_id == Course.id)
    )
    if school_id is not None:
        query = query.filter(Course.school_id == school_id)
    return query


class TrainingReviewService:

    @staticmethod
    def list_pending(db: Session, school_id: int | None):
        return (
            _school_scoped_query(db, school_id)
            .filter(Violation.training_review_status == "PENDING")
            .order_by(Violation.created_at)
            .all()
        )

    @staticmethod
    def review(
        violation_id: int,
        decision: str,
        reviewer_user_id: int,
        school_id: int | None,
        db: Session
    ):
        if decision not in REVIEW_DECISIONS:
            raise HTTPException(
                status_code=400,
                detail=f"decision must be one of {sorted(REVIEW_DECISIONS)}."
            )

        # This had NO school check at all before (not even a wrong one) - any admin could
        # approve/reject any other school's training-review candidates by id. school_id=None
        # (super admin) is the one deliberate exception to this filter.
        violation = _school_scoped_query(db, school_id).filter(Violation.id == violation_id).first()

        if violation is None:
            raise HTTPException(status_code=404, detail="Violation not found.")

        if violation.training_review_status != "PENDING":
            raise HTTPException(
                status_code=400,
                detail="This violation is not awaiting training review."
            )

        violation.training_review_status = decision
        violation.training_reviewed_by = reviewer_user_id
        violation.training_reviewed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(violation)

        AuditLogService.log(
            reviewer_user_id, f"TRAINING_REVIEW_{decision}", "violation", violation_id, db,
            detail=f"event_type={violation.event_type}"
        )

        return violation
