from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.student_answer import StudentAnswer
from app.models.course import Course
from app.models.exam import Exam
from app.models.exam_session import ExamSession
from app.models.instructor import Instructor
from app.models.student import Student
from app.models.subject import Subject
from app.models.user import User
from app.schemas.exam_session import (
    ExamSessionUpdate,
)
from app.services.audit_log_service import AuditLogService
from app.services.exam_service import ExamService
from app.services.face_service import FaceService
from app.services.object_detection_service import ObjectDetectionService
from app.services.risk_service import RiskService


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

        if not student.skip_face_check and student.face_model_path is None:
            raise HTTPException(
                status_code=400,
                detail="Face enrollment is required before starting a proctored exam."
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

        # A prior submitted session doesn't block a new attempt today (that's normal - a student
        # can retake if the instructor reopens the exam). But FLAGGED_RETAKE specifically means
        # "awaiting instructor review" - letting start_exam silently unblock it here would let a
        # student route around the instructor's grant/deny decision entirely. Only the most recent
        # prior session matters - a much older FLAGGED_RETAKE followed by a real RETAKE_GRANTED
        # attempt shouldn't re-block forever.
        latest_session = (
            db.query(ExamSession)
            .filter(
                ExamSession.student_id == student.id,
                ExamSession.exam_id == exam_id,
            )
            .order_by(ExamSession.started_at.desc())
            .first()
        )

        if latest_session is not None and latest_session.status == "FLAGGED_RETAKE":
            raise HTTPException(
                status_code=403,
                detail="This exam was flagged for risk review. Awaiting instructor decision before you can retake it."
            )

        if latest_session is not None and latest_session.status == "RETAKE_DENIED":
            raise HTTPException(
                status_code=403,
                detail="Your instructor denied a retake for this exam."
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
            return (
                db.query(ExamSession)
                .join(Exam, ExamSession.exam_id == Exam.id)
                .join(Subject, Exam.subject_id == Subject.id)
                .join(Course, Subject.course_id == Course.id)
                .filter(Course.school_id == current_user.school_id)
                .all()
            )

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
        session.submitted_at = datetime.now(timezone.utc)

        # passed/score/percentage stay the factual academic result either way - risk is a
        # separate axis. Flagging routes the session to instructor review instead of leaving it
        # simply SUBMITTED; see start_exam's FLAGGED_RETAKE check for what blocks a retake until
        # the instructor grants or denies it (routes/exam_session.py's retake-review endpoint).
        risk_score = RiskService.get_session_summary(session, db)["risk_score"]
        if exam.max_risk_score is not None and risk_score > exam.max_risk_score:
            session.status = "FLAGGED_RETAKE"
        else:
            session.status = "SUBMITTED"

        db.commit()
        db.refresh(session)

        ObjectDetectionService.discard_session(session.id)
        FaceService.discard_session(session.id)

        return session

    @staticmethod
    def review_retake(session_id: int, decision: str, db: Session):

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

        if session.status != "FLAGGED_RETAKE":
            raise HTTPException(
                status_code=400,
                detail="This session is not flagged for retake review."
            )

        if decision == "GRANT":
            # Unblocks start_exam's FLAGGED_RETAKE check - this session stays as the historical
            # record, the student's next start_exam call creates a fresh one.
            session.status = "RETAKE_GRANTED"
        elif decision == "DENY":
            # A distinct terminal status, not just leaving it as FLAGGED_RETAKE - the instructor
            # needs to see "already reviewed, denied" instead of an appeal that still looks
            # pending. start_exam blocks on both FLAGGED_RETAKE and RETAKE_DENIED; only
            # RETAKE_GRANTED unblocks. This is the fail-with-no-retake outcome.
            session.status = "RETAKE_DENIED"
        else:
            raise HTTPException(
                status_code=400,
                detail="decision must be GRANT or DENY."
            )

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
        actor_user_id: int,
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

        # Captured before delete - a deleted session's violations cascade away with it (see
        # Violation.exam_session's cascade="all, delete-orphan"), so this audit row is the only
        # surviving record that a session (and any proctoring evidence logged against it) ever
        # existed. Without this, an admin/instructor could silently erase exam-session history
        # with zero trace - a real gap for a proctoring system specifically.
        detail = f"student_id={session.student_id} exam_id={session.exam_id} status={session.status}"

        db.delete(session)
        db.commit()

        AuditLogService.log(
            actor_user_id, "DELETE_EXAM_SESSION", "exam_session", session_id, db, detail=detail
        )

        return {
            "message": "Session deleted successfully."
        }