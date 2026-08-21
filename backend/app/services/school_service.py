from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.auth.service import AuthService
from app.models.school import School
from app.schemas.school import SchoolRegisterRequest, SchoolUpdate
from app.utils.slugify import slugify


class SchoolService:

    @staticmethod
    def get_all(db: Session):
        return db.query(School).all()

    @staticmethod
    def get_by_id(school_id: int, db: Session) -> School:
        school = db.query(School).filter(School.id == school_id).first()
        if school is None:
            raise HTTPException(status_code=404, detail="School not found.")
        return school

    @staticmethod
    def update(school_id: int, request: SchoolUpdate, db: Session) -> School:
        school = SchoolService.get_by_id(school_id, db)

        if request.code is not None:
            duplicate = (
                db.query(School)
                .filter(School.code == request.code, School.id != school_id)
                .first()
            )
            if duplicate:
                raise HTTPException(status_code=400, detail="A school with this code already exists.")
            school.code = request.code

        if request.slug is not None:
            slug = slugify(request.slug)
            if not slug:
                raise HTTPException(status_code=400, detail="Invalid school URL slug.")
            duplicate = (
                db.query(School)
                .filter(School.slug == slug, School.id != school_id)
                .first()
            )
            if duplicate:
                raise HTTPException(status_code=400, detail="A school with this URL is already registered.")
            school.slug = slug

        if request.name is not None:
            school.name = request.name

        if request.is_active is not None:
            school.is_active = request.is_active

        db.commit()
        db.refresh(school)

        return school

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

        slug = slugify(request.slug)
        if not slug:
            raise HTTPException(
                status_code=400,
                detail="Invalid school URL slug."
            )

        slug_taken = (
            db.query(School)
            .filter(School.slug == slug)
            .first()
        )
        if slug_taken:
            raise HTTPException(
                status_code=400,
                detail="A school with this URL is already registered."
            )

        school = School(code=request.code, name=request.name, slug=slug)
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
