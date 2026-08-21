from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import is_super_admin
from app.auth.service import AuthService
from app.models.instructor import Instructor
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
            request.username, request.email, request.password,
            request.first_name, request.last_name, "instructor", current_user.school_id, db,
        )

        instructor = Instructor(
            employee_number=request.employee_number,
            user_id=user.id
        )

        db.add(instructor)
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

        db.delete(instructor)
        db.commit()

        return {
            "message": "Instructor deleted successfully."
        }