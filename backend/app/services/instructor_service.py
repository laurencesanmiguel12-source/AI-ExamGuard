from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import is_super_admin
from app.auth.service import AuthService
from app.models.course import Course
from app.models.exam import Exam
from app.models.instructor import Instructor
from app.models.instructor_subject import InstructorSubject
from app.models.subject import Subject
from app.models.user import User
from app.schemas.instructor import (
    InstructorCreate,
    InstructorUpdate
)


class InstructorService:

    @staticmethod
    def get_all(current_user: User, db: Session):
        query = db.query(Instructor).join(User, Instructor.user_id == User.id)
        if not is_super_admin(current_user):
            query = query.filter(User.school_id == current_user.school_id)
        return query.all()

    @staticmethod
    def get_by_id(instructor_id: int, current_user: User, db: Session):

        instructor = (
            db.query(Instructor)
            .filter(Instructor.id == instructor_id)
            .first()
        )

        if instructor is None:
            raise HTTPException(
                status_code=404,
                detail="Instructor not found."
            )

        if not is_super_admin(current_user) and instructor.user.school_id != current_user.school_id:
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to manage this instructor."
            )

        return instructor

    @staticmethod
    def create(request: InstructorCreate, current_user: User, db: Session):

        existing = (
            db.query(Instructor)
            .join(User, Instructor.user_id == User.id)
            .filter(
                Instructor.employee_number == request.employee_number,
                User.school_id == current_user.school_id,
            )
            .first()
        )

        if existing:
            raise HTTPException(
                status_code=400,
                detail="Employee number already exists."
            )

        # school_id is always the calling admin's own school, never client-supplied - same
        # never-trust-the-client derivation as Exam.instructor_id.
        user = AuthService.create_user_account(
            request.email, request.password,
            request.first_name, request.last_name, "instructor", current_user.school_id, db,
        )

        instructor = Instructor(
            employee_number=request.employee_number,
            user_id=user.id
        )

        db.add(instructor)
        db.flush()  # assigns instructor.id for the subject links below, without committing

        # Same school check the standalone POST /instructors/{id}/subjects assignment does - a
        # subject belongs to a Course, which belongs to a School.
        for subject_id in dict.fromkeys(request.subject_ids):
            subject_school_id = (
                db.query(Course.school_id)
                .join(Subject, Subject.course_id == Course.id)
                .filter(Subject.id == subject_id)
                .scalar()
            )
            if subject_school_id is None:
                raise HTTPException(status_code=404, detail=f"Subject {subject_id} not found.")
            if subject_school_id != current_user.school_id:
                raise HTTPException(
                    status_code=403,
                    detail=f"Subject {subject_id} belongs to another school."
                )
            db.add(InstructorSubject(instructor_id=instructor.id, subject_id=subject_id))

        db.commit()
        db.refresh(instructor)

        return instructor

    @staticmethod
    def update(
        instructor_id: int,
        request: InstructorUpdate,
        current_user: User,
        db: Session
    ):

        instructor = InstructorService.get_by_id(
            instructor_id,
            current_user,
            db
        )

        if request.employee_number is not None:
            instructor.employee_number = request.employee_number

        db.commit()
        db.refresh(instructor)

        return instructor

    @staticmethod
    def delete(
        instructor_id: int,
        current_user: User,
        db: Session
    ):

        instructor = InstructorService.get_by_id(
            instructor_id,
            current_user,
            db
        )

        # exams.instructor_id has no ON DELETE, so this would otherwise surface as an
        # IntegrityError 500 rather than something the caller can act on.
        owned_exams = db.query(Exam).filter(Exam.instructor_id == instructor.id).count()
        if owned_exams:
            raise HTTPException(
                status_code=400,
                detail=f"This instructor still owns {owned_exams} exam(s) - reassign or delete "
                       f"them first."
            )

        # Delete the login too. Removing only the Instructor row left the User behind with
        # role="instructor" and no profile: still able to log in, and landing in a broken state
        # where every exam route 403s ("no linked instructor profile"). Unlike
        # AdminUserService.update_role - which deliberately keeps a profile row so a later
        # re-promotion restores its context - there is nothing here to preserve, since the
        # profile row is exactly what is being destroyed.
        user = instructor.user
        db.query(InstructorSubject).filter(
            InstructorSubject.instructor_id == instructor.id
        ).delete(synchronize_session=False)
        db.delete(instructor)
        if user is not None:
            db.delete(user)
        db.commit()

        return {
            "message": "Instructor deleted successfully."
        }