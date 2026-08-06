from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.exam import Exam
from app.models.exam_roster import ExamRoster
from app.models.instructor import Instructor
from app.models.instructor_subject import InstructorSubject
from app.models.student import Student
from app.models.subject import Subject
from app.models.user import User
from app.schemas.exam import ExamCreate, ExamUpdate


class ExamService:

    @staticmethod
    def _require_subject_assignment(instructor_id: int, subject_id: int, db: Session) -> None:
        assigned = (
            db.query(InstructorSubject)
            .filter(
                InstructorSubject.instructor_id == instructor_id,
                InstructorSubject.subject_id == subject_id,
            )
            .first()
        )
        if assigned is None:
            raise HTTPException(
                status_code=403,
                detail="Instructor is not assigned to this subject."
            )

    @staticmethod
    def is_student_eligible(student: Student, exam: Exam, db: Session) -> bool:
        subject = db.query(Subject).filter(Subject.id == exam.subject_id).first()
        if subject is None or subject.course_id != student.course_id:
            return False

        # Opt-in narrowing: an exam with no roster rows stays course-wide (today's default
        # behavior). The moment an instructor rosters >=1 student, it's restricted to just them.
        has_roster = (
            db.query(ExamRoster)
            .filter(ExamRoster.exam_id == exam.id)
            .first()
            is not None
        )
        if not has_roster:
            return True

        return (
            db.query(ExamRoster)
            .filter(ExamRoster.exam_id == exam.id, ExamRoster.student_id == student.id)
            .first()
            is not None
        )

    @staticmethod
    def get_all(current_user: User, db: Session):

        if current_user.role.name.lower() != "student":
            return db.query(Exam).all()

        student = db.query(Student).filter(Student.user_id == current_user.id).first()
        if student is None:
            return []

        course_wide_candidates = (
            db.query(Exam)
            .join(Subject, Exam.subject_id == Subject.id)
            .filter(Subject.course_id == student.course_id)
            .all()
        )

        return [
            exam for exam in course_wide_candidates
            if ExamService.is_student_eligible(student, exam, db)
        ]

    @staticmethod
    def get_by_id(exam_id: int, db: Session):

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

        return exam

    @staticmethod
    def get_by_id_for_user(exam_id: int, current_user: User, db: Session):

        exam = ExamService.get_by_id(exam_id, db)

        if current_user.role.name.lower() == "student":
            student = db.query(Student).filter(Student.user_id == current_user.id).first()
            if student is None or not ExamService.is_student_eligible(student, exam, db):
                raise HTTPException(
                    status_code=403,
                    detail="This exam is not available for your course."
                )

        return exam

    @staticmethod
    def create(instructor: Instructor, request: ExamCreate, db: Session):

        subject = (
            db.query(Subject)
            .filter(Subject.id == request.subject_id)
            .first()
        )

        if subject is None:
            raise HTTPException(
                status_code=404,
                detail="Subject not found."
            )

        ExamService._require_subject_assignment(instructor.id, subject.id, db)

        # instructor_id is always the caller's own instructor record, never taken from the
        # request body - see backend/app/auth/instructor_context.py's get_current_instructor.
        exam_data = request.model_dump(exclude={"instructor_id"})
        exam = Exam(**exam_data, instructor_id=instructor.id)

        db.add(exam)
        db.commit()
        db.refresh(exam)

        return exam

    @staticmethod
    def update(exam_id: int, request: ExamUpdate, db: Session):

        exam = ExamService.get_by_id(exam_id, db)

        update_data = request.model_dump(exclude_unset=True)

        if "subject_id" in update_data and update_data["subject_id"] != exam.subject_id:
            ExamService._require_subject_assignment(exam.instructor_id, update_data["subject_id"], db)

        for key, value in update_data.items():
            setattr(exam, key, value)

        db.commit()
        db.refresh(exam)

        return exam

    @staticmethod
    def delete(exam_id: int, db: Session):

        exam = ExamService.get_by_id(exam_id, db)

        db.delete(exam)
        db.commit()

        return {
            "message": "Exam deleted successfully."
        }
