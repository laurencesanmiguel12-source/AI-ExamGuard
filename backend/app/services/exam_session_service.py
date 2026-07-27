from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.student_answer import StudentAnswer
from app.models.exam import Exam
from app.models.exam_session import ExamSession
from app.models.instructor import Instructor
from app.models.student import Student
from app.models.user import User
from app.schemas.exam_session import (
    ExamSessionUpdate,
)
from app.services.exam_service import ExamService


class ExamSessionService:

    @staticmethod
    def start_exam(
        student: Student,
        exam_id: int,
        db: Session
    ):

        exam = (
            db.query(Exam)
            .filter(Exam.id == exam_id)
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

        if not ExamService.is_student_eligible(student, exam, db):
            raise HTTPException(
                status_code=403,
                detail="This exam is not available for your course."
            )

        existing_session = (
            db.query(ExamSession)
            .filter(
                ExamSession.student_id == student.id,
                ExamSession.exam_id == exam_id,
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
            student_id=student.id,
            exam_id=exam_id,
            started_at=datetime.now(),
            status="IN_PROGRESS"
        )

        db.add(session)
        db.commit()
        db.refresh(session)

        return session

    @staticmethod
    def get_all(current_user: User, db: Session):

        role = current_user.role.name.lower()

        if role == "admin":
            return db.query(ExamSession).all()

        if role == "instructor":
            instructor = (
                db.query(Instructor)
                .filter(Instructor.user_id == current_user.id)
                .first()
            )
            if instructor is None:
                return []
            return (
                db.query(ExamSession)
                .join(Exam, ExamSession.exam_id == Exam.id)
                .filter(Exam.instructor_id == instructor.id)
                .all()
            )

        student = db.query(Student).filter(Student.user_id == current_user.id).first()
        if student is None:
            return []
        return db.query(ExamSession).filter(ExamSession.student_id == student.id).all()

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
                detail="Exam session not found."
            )

        if session.status != "IN_PROGRESS":
            raise HTTPException(
                status_code=400,
                detail="Exam already submitted."
            )

        exam = (
            db.query(Exam)
            .filter(Exam.id == session.exam_id)
            .first()
        )

        if exam is None:
            raise HTTPException(
                status_code=404,
                detail="Exam not found."
            )

        answers = (
            db.query(StudentAnswer)
            .filter(
                StudentAnswer.exam_session_id == session.id
            )
            .all()
        )

        total_score = sum(
            answer.points_awarded
            for answer in answers
        )

        if exam.total_points > 0:
            percentage = (
                                 total_score / exam.total_points
                         ) * 100
        else:
            percentage = 0

        passed = percentage >= exam.passing_score

        session.score = total_score
        session.percentage = percentage
        session.passed = passed

        session.status = "SUBMITTED"
        session.submitted_at = datetime.now(timezone.utc)

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