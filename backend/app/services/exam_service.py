from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import is_super_admin
from app.models.course import Course
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

        # Roster-required by default (changed 2026-08-20 from opt-in narrowing, where an
        # exam with zero roster rows was course-wide by default): a student is only eligible
        # once an instructor has explicitly rostered them for this specific exam. This was a
        # deliberate policy flip, not a bug fix - live production feedback was that a newly
        # self-registered student seeing every unrostered course exam immediately was the wrong
        # default for this deployment.
        return (
            db.query(ExamRoster)
            .filter(ExamRoster.exam_id == exam.id, ExamRoster.student_id == student.id)
            .first()
            is not None
        )

    @staticmethod
    def get_all(current_user: User, db: Session):

        if current_user.role.name.lower() != "student":
            # Previously db.query(Exam).all() - every exam in the entire deployment, with zero
            # scoping. Harmless in the single-school world this was written in; a direct
            # cross-tenant leak the moment a second school shares this deployment. Super admin
            # deliberately skips the filter - that's its one legitimate use.
            query = (
                db.query(Exam)
                .join(Subject, Exam.subject_id == Subject.id)
                .join(Course, Subject.course_id == Course.id)
            )
            if not is_super_admin(current_user):
                query = query.filter(Course.school_id == current_user.school_id)

            # Instructors get only their own exams. Every exam *action* is owner-gated by
            # require_exam_owner, so listing the whole school's exams to an instructor promised
            # access the detail routes then refused: Exams.jsx renders a "View roster" link on
            # every row, and a newly created instructor (who owns nothing yet) saw a full list
            # where every single roster link 403'd. Reported live as "new instructor cannot see
            # student roster". Admins still get the whole school - they legitimately manage all
            # of it - and the instructor dashboard already filtered to instructor_id == me.
            if current_user.role.name.lower() == "instructor":
                instructor = (
                    db.query(Instructor)
                    .filter(Instructor.user_id == current_user.id)
                    .first()
                )
                if instructor is None:
                    return []
                query = query.filter(Exam.instructor_id == instructor.id)

            return query.all()

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
        elif not is_super_admin(current_user):
            exam_school_id = (
                db.query(Course.school_id)
                .join(Subject, Subject.course_id == Course.id)
                .filter(Subject.id == exam.subject_id)
                .scalar()
            )
            if exam_school_id != current_user.school_id:
                raise HTTPException(
                    status_code=404,
                    detail="Exam not found."
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
