import os

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.course import Course
from app.models.exam import Exam
from app.models.exam_session import ExamSession
from app.models.near_miss_capture import NearMissCapture
from app.models.subject import Subject
from app.services.audit_log_service import AuditLogService

STORAGE_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "storage", "near_miss_evidence"
)

REVIEW_DECISIONS = {"APPROVED", "REJECTED"}


def _school_scoped_query(db: Session, school_id: int | None):
    """Same tenant scoping the violation review queue uses - a school admin must only ever see
    frames captured during their own school's exams."""
    query = (
        db.query(NearMissCapture)
        .join(ExamSession, NearMissCapture.exam_session_id == ExamSession.id)
        .join(Exam, ExamSession.exam_id == Exam.id)
        .join(Subject, Exam.subject_id == Subject.id)
        .join(Course, Subject.course_id == Course.id)
    )
    if school_id is not None:
        query = query.filter(Course.school_id == school_id)
    return query


class NearMissCaptureService:

    @staticmethod
    def capture(session_id: int, detector: str, confidence: float, image_bytes: bytes | None,
                db: Session) -> NearMissCapture | None:
        """Keeps a frame the detector found plausible but did not act on.

        Runs on the hot detection path, so it is written to be impossible for this to break a
        proctoring poll: it returns None rather than raising for every reason it might decline,
        and the caller ignores the result. A failure here costs one training sample; an exception
        here would cost the student their exam.
        """
        # Import here rather than at module scope: object_detection_service imports this module,
        # and importing it back at the top would be a cycle.
        from app.services import object_detection_service as ods

        if image_bytes is None:
            return None
        if confidence < ods.NEAR_MISS_CONFIDENCE_FLOOR:
            return None
        if ods._near_miss_counts.get(session_id, 0) >= ods.NEAR_MISS_MAX_PER_SESSION:
            return None

        try:
            capture = NearMissCapture(
                exam_session_id=session_id,
                detector=detector,
                confidence=float(confidence),
                training_review_status="PENDING",
            )
            db.add(capture)
            db.flush()  # assigns the id the filename is built from

            os.makedirs(STORAGE_DIR, exist_ok=True)
            path = os.path.join(STORAGE_DIR, f"{capture.id}.jpg")
            with open(path, "wb") as f:
                f.write(image_bytes)
            capture.evidence_path = path

            db.commit()
            ods._near_miss_counts[session_id] = ods._near_miss_counts.get(session_id, 0) + 1
            return capture
        except Exception:
            # Deliberately broad, for the reason in the docstring. Nothing downstream depends on
            # a capture succeeding.
            db.rollback()
            return None

    @staticmethod
    def list_pending(db: Session, school_id: int | None):
        """Highest confidence first: the frames that came closest to firing are the ones a
        reviewer should judge while they have the most context, and the ones whose labels move
        the decision boundary most."""
        return (
            _school_scoped_query(db, school_id)
            .filter(NearMissCapture.training_review_status == "PENDING")
            .order_by(NearMissCapture.confidence.desc())
            .all()
        )

    @staticmethod
    def get_for_school(capture_id: int, db: Session, school_id: int | None) -> NearMissCapture:
        capture = (
            _school_scoped_query(db, school_id)
            .filter(NearMissCapture.id == capture_id)
            .first()
        )
        if capture is None:
            raise HTTPException(status_code=404, detail="Capture not found.")
        return capture

    @staticmethod
    def review(capture_id: int, decision: str, reviewer_id: int, db: Session,
               school_id: int | None) -> NearMissCapture:
        if decision not in REVIEW_DECISIONS:
            raise HTTPException(
                status_code=400,
                detail=f"decision must be one of {sorted(REVIEW_DECISIONS)}."
            )

        capture = NearMissCaptureService.get_for_school(capture_id, db, school_id)

        if capture.training_review_status != "PENDING":
            raise HTTPException(
                status_code=400,
                detail=f"This capture has already been reviewed ({capture.training_review_status})."
            )

        capture.training_review_status = decision
        AuditLogService.log(
            actor_user_id=reviewer_id,
            action=f"NEAR_MISS_{decision}",
            resource_type="near_miss_capture",
            resource_id=capture.id,
            db=db,
        )
        db.commit()
        db.refresh(capture)
        return capture
