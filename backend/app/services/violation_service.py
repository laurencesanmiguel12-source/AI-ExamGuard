import os
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.exam_session import ExamSession
from app.models.violation import Violation
from app.schemas.violation import ViolationCreate

# Vision-based violation types have a webcam frame available at detection time. AI_TOOL_DETECTED/
# SEARCH_ENGINE_DETECTED get a screenshot of the offending tab instead, captured by the extension
# itself (see extension/background.js) - genuinely optional, since captureVisibleTab only works
# when that tab happens to be the active one at the moment of detection. Purely behavioral events
# (tab-switch, copy-paste, right-click, fullscreen-exit) have no visual counterpart to save at all.
EVIDENCE_EVENT_TYPES = {
    "FACE_LOST", "IDENTITY_MISMATCH", "PHONE_DETECTED", "MULTIPLE_PEOPLE",
    "AI_TOOL_DETECTED", "SEARCH_ENGINE_DETECTED", "STATIC_IMAGE_SUSPECTED",
}

STORAGE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "storage",
    "violation_evidence"
)

APPEAL_DECISIONS = {"UPHELD", "OVERTURNED"}


class ViolationService:

    @staticmethod
    def log_violation(
        session_id: int,
        request: ViolationCreate,
        db: Session,
        evidence_bytes: bytes | None = None,
        question_id: int | None = None,
        question_text: str | None = None,
        question_type: str | None = None
    ):

        session = (
            db.query(ExamSession)
            .filter(ExamSession.id == session_id)
            .first()
        )

        if session is None:
            raise HTTPException(
                status_code=404,
                detail="Exam session not found."
            )

        if session.status != "IN_PROGRESS":
            raise HTTPException(
                status_code=400,
                detail="Exam session is not in progress."
            )

        # question_id/text/type deliberately aren't on ViolationCreate (the schema the
        # student-facing POST /violations route accepts) - like evidence_bytes below, this is a
        # server-detected snapshot, not something a client should be able to submit and have
        # trusted at face value.
        violation = Violation(
            exam_session_id=session_id,
            event_type=request.event_type,
            detail=request.detail,
            question_id=question_id,
            question_text=question_text,
            question_type=question_type
        )

        db.add(violation)
        db.commit()
        db.refresh(violation)

        if evidence_bytes and request.event_type in EVIDENCE_EVENT_TYPES:
            os.makedirs(STORAGE_DIR, exist_ok=True)
            evidence_path = os.path.join(STORAGE_DIR, f"{violation.id}.jpg")
            with open(evidence_path, "wb") as f:
                f.write(evidence_bytes)

            violation.evidence_path = evidence_path
            db.commit()
            db.refresh(violation)

        return violation

    @staticmethod
    def get_violations(
        session_id: int,
        db: Session
    ):

        return (
            db.query(Violation)
            .filter(Violation.exam_session_id == session_id)
            .order_by(Violation.created_at.desc())
            .all()
        )

    @staticmethod
    def get_evidence_path(
        violation_id: int,
        db: Session
    ) -> str:

        violation = db.query(Violation).filter(Violation.id == violation_id).first()

        if violation is None or violation.evidence_path is None:
            raise HTTPException(
                status_code=404,
                detail="No evidence recorded for this violation."
            )

        return violation.evidence_path

    @staticmethod
    def file_appeal(
        violation_id: int,
        reason: str,
        db: Session
    ):

        violation = db.query(Violation).filter(Violation.id == violation_id).first()

        if violation is None:
            raise HTTPException(status_code=404, detail="Violation not found.")

        if violation.appeal_status is not None:
            raise HTTPException(
                status_code=400,
                detail="This violation has already been appealed."
            )

        violation.appeal_reason = reason
        violation.appeal_status = "PENDING"
        db.commit()
        db.refresh(violation)

        return violation

    @staticmethod
    def review_appeal(
        violation_id: int,
        decision: str,
        response_text: str,
        reviewer_user_id: int,
        db: Session
    ):

        if decision not in APPEAL_DECISIONS:
            raise HTTPException(
                status_code=400,
                detail=f"status must be one of {sorted(APPEAL_DECISIONS)}."
            )

        violation = db.query(Violation).filter(Violation.id == violation_id).first()

        if violation is None:
            raise HTTPException(status_code=404, detail="Violation not found.")

        if violation.appeal_status != "PENDING":
            raise HTTPException(
                status_code=400,
                detail="This violation has no pending appeal to review."
            )

        violation.appeal_status = decision
        violation.appeal_response = response_text
        violation.appeal_reviewed_by = reviewer_user_id
        violation.appeal_reviewed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(violation)

        return violation
