from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.exam import Exam
from app.models.exam_session import ExamSession
from app.models.student import Student
from app.schemas.exam_session import (
    ExamSessionCreate,
    ExamSessionUpdate,
)


class ExamSessionService:

    @staticmethod
    def start_exam(
        request: ExamSessionCreate,
        db: Session
    ):

        student = (
            db.query(Student)
            .filter(Student.id == request.student_id)
            .first()
        )

        if student is None:
            raise HTTPException(
                status_code=404,
                detail="Student not found."
            )

        exam = (
            db.query(Exam)
            .filter(Exam.id == request.exam_id)
            .first()
        )

        if exam is None:
            raise HTTPException(
                status_code=404,
                detail="Exam not found."
            )

        if not exam.is_active:
            raise HTTPException(
                status_code=400,
                detail="Exam is not active."
            )

        existing_session = (
            db.query(ExamSession)
            .filter(
                ExamSession.student_id == request.student_id,
                ExamSession.exam_id == request.exam_id,
                ExamSession.status == "IN_PROGRESS"
            )
            .first()
        )

        if existing_session:
            raise HTTPException(
                status_code=400,
                detail="Student already has an active session."
            )

        session = ExamSession(
            student_id=request.student_id,
            exam_id=request.exam_id,
            started_at=datetime.now(),
            status="IN_PROGRESS"
        )

        db.add(session)
        db.commit()
        db.refresh(session)

        return session

    @staticmethod
    def get_all(db: Session):

        return db.query(ExamSession).all()

    @staticmethod
    def get_by_id(
        session_id: int,
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
                detail="Session not found."
            )

        return session

    @staticmethod
    def submit_exam(
        session_id: int,
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
                detail="Session not found."
            )

        if session.status == "SUBMITTED":
            raise HTTPException(
                status_code=400,
                detail="Exam already submitted."
            )

        session.status = "SUBMITTED"
        session.submitted_at = datetime.now()

        db.commit()
        db.refresh(session)

        return session

    @staticmethod
    def update(
        session_id: int,
        request: ExamSessionUpdate,
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
                detail="Session not found."
            )

        update_data = request.model_dump(exclude_unset=True)

        for key, value in update_data.items():
            setattr(session, key, value)

        db.commit()
        db.refresh(session)

        return session

    @staticmethod
    def delete(
        session_id: int,
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
                detail="Session not found."
            )

        db.delete(session)
        db.commit()

        return {
            "message": "Session deleted successfully."
        }