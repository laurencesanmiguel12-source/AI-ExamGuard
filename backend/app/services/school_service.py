from datetime import datetime, timezone

from fastapi import BackgroundTasks, HTTPException
from sqlalchemy.orm import Session

from app.auth.service import AuthService
from app.models.school import (
    SCHOOL_APPROVED,
    SCHOOL_PENDING,
    SCHOOL_REJECTED,
    School,
)
from app.models.user import User
from app.schemas.school import SchoolRegisterRequest, SchoolReviewRequest, SchoolUpdate
from app.services.notification_service import NotificationService
from app.utils.slugify import slugify


class SchoolService:

    @staticmethod
    def get_all(db: Session):
        """Public and unauthenticated - this feeds the student-registration form's school picker,
        so it must only ever list schools that can actually be registered into and logged in to.
        A pending or rejected school appearing here would let students sign up into a school
        whose own admin cannot log in yet. Super admins get the unfiltered list through
        get_all_for_review instead."""
        return db.query(School).filter(School.status == SCHOOL_APPROVED).all()

    @staticmethod
    def get_all_for_review(db: Session, status: str | None = None):
        query = db.query(School)
        if status is not None:
            query = query.filter(School.status == status)
        return query.order_by(School.created_at.desc()).all()

    @staticmethod
    def get_public_by_slug(slug: str, db: Session) -> School:
        """Public, and deliberately NOT filtered by status - the login page needs to resolve a
        pending or rejected school in order to explain what happened to the person who registered
        it. Returns the School; the response schema decides what is safe to expose."""
        school = db.query(School).filter(School.slug == slug).first()
        if school is None:
            raise HTTPException(status_code=404, detail="School not found.")
        return school

    @staticmethod
    def review(school_id: int, request: SchoolReviewRequest, reviewer: User, db: Session,
               background_tasks: BackgroundTasks | None = None):
        school = SchoolService.get_by_id(school_id, db)

        if request.status not in (SCHOOL_APPROVED, SCHOOL_REJECTED):
            raise HTTPException(
                status_code=400,
                detail=f"status must be '{SCHOOL_APPROVED}' or '{SCHOOL_REJECTED}'."
            )

        if school.status != SCHOOL_PENDING:
            raise HTTPException(
                status_code=400,
                detail=f"This school has already been reviewed (currently '{school.status}')."
            )

        school.status = request.status
        school.review_note = request.review_note
        school.reviewed_at = datetime.now(timezone.utc)
        school.reviewed_by_user_id = reviewer.id

        db.commit()
        db.refresh(school)

        # Queued after the commit, never before: the decision is what matters and it is already
        # durable by this point. A mail failure is logged inside NotificationService and cannot
        # roll the review back or fail the request.
        if background_tasks is not None:
            if school.status == SCHOOL_APPROVED:
                background_tasks.add_task(
                    NotificationService.notify_school_approved,
                    school.name, school.slug, school.id, school.review_note, db,
                )
            else:
                background_tasks.add_task(
                    NotificationService.notify_school_rejected,
                    school.name, school.id, school.review_note, db,
                )

        return school

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
    def register(request: SchoolRegisterRequest, db: Session,
                 background_tasks: BackgroundTasks | None = None):

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

        # Created pending, not live: a self-service signup is a request to join the platform, and
        # a super admin approves it before anyone at that school can log in (see
        # AuthService.login's status check). The founding admin account below is still created
        # right now, in the same transaction, so approval needs no second act from the applicant -
        # their existing credentials simply start working.
        school = School(code=request.code, name=request.name, slug=slug, status=SCHOOL_PENDING)
        db.add(school)
        db.flush()  # assigns school.id without committing, for the admin user below

        # First-ever way to create a role="admin" account in this codebase - previously always a
        # raw DB seed, no route existed. Reuses the same duplicate-check/role-lookup/User-creation
        # helper every other account type (student self-registration, admin-created
        # instructor/student) already goes through.
        AuthService.create_user_account(
            request.email, request.password,
            request.first_name, request.last_name, "admin", school.id, db,
        )

        db.commit()
        db.refresh(school)

        # Queued only after the commit succeeds, so we never announce a signup that then rolled
        # back. Best-effort by design: this endpoint is public and unauthenticated, and an SMTP
        # outage must not turn a valid registration into an error for the applicant.
        if background_tasks is not None:
            background_tasks.add_task(
                NotificationService.notify_school_pending_review,
                school.name, school.code, request.email, db,
            )

        return school
