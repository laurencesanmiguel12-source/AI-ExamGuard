from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.auth.service import AuthService
from app.models.school import School
from app.schemas.school import SchoolRegisterRequest


class SchoolService:

    @staticmethod
    def get_all(db: Session):
        return db.query(School).all()

    @staticmethod
    def register(request: SchoolRegisterRequest, db: Session):

        existing = (
            db.query(School)
            .filter(School.code == request.code)
            .first()
        )

        if existing:
            raise HTTPException(
                status_code=400,
                detail="A school with this code already exists."
            )

        school = School(code=request.code, name=request.name)
        db.add(school)
        db.flush()  # assigns school.id without committing, for the admin user below

        # First-ever way to create a role="admin" account in this codebase - previously always a
        # raw DB seed, no route existed. Reuses the same duplicate-check/role-lookup/User-creation
        # helper every other account type (student self-registration, admin-created
        # instructor/student) already goes through.
        AuthService.create_user_account(
            request.username, request.email, request.password,
            request.first_name, request.last_name, "admin", school.id, db,
        )

        db.commit()
        db.refresh(school)

        return school
