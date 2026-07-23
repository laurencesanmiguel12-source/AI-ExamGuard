from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.exam_session import ExamSession
from app.models.violation import Violation
from app.schemas.violation import ViolationCreate


class ViolationService:

    @staticmethod
    def log_violation(
        session_id: int,
        request: ViolationCreate,
        db: Session
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

        violation = Violation(
            exam_session_id=session_id,
            event_type=request.event_type
        )

        db.add(violation)
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
