from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.auth.service import AuthService
from app.models.instructor import Instructor
from app.models.user import User
from app.schemas.instructor import (
    InstructorCreate,
    InstructorUpdate
)


class InstructorService:

    @staticmethod
    def get_all(db: Session):
        return db.query(Instructor).all()

    @staticmethod
    def get_by_id(instructor_id: int, db: Session):

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

        return instructor

    @staticmethod
    def create(request: InstructorCreate, db: Session):

        existing = (
            db.query(Instructor)
            .filter(
                Instructor.employee_number == request.employee_number
            )
            .first()
        )

        if existing:
            raise HTTPException(
                status_code=400,
                detail="Employee number already exists."
            )

        user = AuthService.create_user_account(
            request.username, request.email, request.password,
            request.first_name, request.last_name, "instructor", db,
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
        db: Session
    ):

        instructor = InstructorService.get_by_id(
            instructor_id,
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
        db: Session
    ):

        instructor = InstructorService.get_by_id(
            instructor_id,
            db
        )

        db.delete(instructor)
        db.commit()

        return {
            "message": "Instructor deleted successfully."
        }