from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth.security import hash_password
from app.schemas.email_typo import check_email_typo
from app.models.course import Course
from app.models.role import Role
from app.models.school import SCHOOL_APPROVED, SCHOOL_PENDING, SCHOOL_REJECTED, School
from app.models.student import Student
from app.models.user import User
from app.schemas.auth import RegisterRequest
from app.schemas.auth import LoginRequest
from app.auth.jwt import create_access_token
from app.auth.security import verify_password


class AuthService:

    @staticmethod
    def create_user_account(
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        role_name: str,
        school_id: int,
        db: Session,
    ) -> User:
        """Shared by school signup (role_name="admin"), public self-registration (always
        role_name="student"), and the admin-only instructor/student creation endpoints - same
        duplicate-checks + role lookup + User row every account needs, just with the role, school,
        and linked profile row differing. Leaves the transaction open (flush, not commit) so the
        caller can add its profile row (Student/Instructor) and commit both together."""

        # Real bug found live: this and login() below both used a case-sensitive `==` on email,
        # so "Name@gmail.com" and "name@gmail.com" were treated as two different addresses -
        # registration let a real duplicate account through untouched (confirmed: registering an
        # already-used email in a different case returned 200, not the expected 400), and the
        # matching case-sensitive lookup in login() meant the ORIGINAL account became
        # unreachable the moment someone typed their own email back in a different case than
        # they happened to register with - indistinguishable from "this email was never
        # registered" from the user's side. Gmail addresses specifically are case-insensitive by
        # convention, so this wasn't a hypothetical edge case for a real @gmail.com account hit
        # by it. Normalizing (strip + lowercase) at creation, and comparing case-insensitively
        # here and in login(), fixes both directions without needing to touch any already-stored
        # row - existing mixed-case emails still match correctly against a case-insensitive
        # comparison.
        email = email.strip().lower()

        # There is deliberately no username here. The column was globally unique across every
        # school while nothing ever read it - login(), get_current_user() and every lookup in this
        # codebase key on email - so its only live effect was rejecting a registration with
        # "Username already exists." when some unrelated school's user had already taken the name.
        # Reported symptom was instructors finding students missing from their rosters: those
        # students had never successfully registered at all.
        existing_email = (
            db.query(User)
            .filter(func.lower(User.email) == email)
            .first()
        )

        if existing_email:
            raise HTTPException(
                status_code=400,
                detail="Email already exists."
            )

        role = db.query(Role).filter(Role.name.ilike(role_name)).first()
        if role is None:
            raise HTTPException(
                status_code=500,
                detail=f"{role_name.title()} role is not configured."
            )

        user = User(
            email=email,
            first_name=first_name,
            last_name=last_name,
            password_hash=hash_password(password),
            role_id=role.id,
            school_id=school_id,
            is_active=True
        )
        db.add(user)
        db.flush()  # assigns user.id without committing, for the caller's profile row

        return user

    @staticmethod
    def update_user_identity(
        user: User,
        db: Session,
        email: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> User:
        """Change the name or sign-in address on an existing account.

        Shared by instructor and student editing, because those are the same act on two different
        profile rows. Until now neither could be changed at all: the edit forms carried only the
        employee/student number, so a misspelled name or a wrong email address - the exact thing
        somebody opens an edit form to fix - had to be corrected in the database.

        The email path repeats create_user_account's normalisation and case-insensitive duplicate
        check for the reason documented there: without it "Name@x.com" and "name@x.com" become two
        accounts, and the original becomes unreachable at login. Leaves the transaction open; the
        caller commits alongside whatever else it is changing.
        """
        if first_name is not None:
            user.first_name = first_name
        if last_name is not None:
            user.last_name = last_name

        if email is not None:
            normalised = email.strip().lower()
            if normalised != (user.email or "").strip().lower():
                # Only on an actual CHANGE. The guard belongs here rather than on the schema
                # because a field validator cannot see the address the record already has - and
                # jrizal@gmail.cmo is a real row in the live database, the one the guard was
                # written for. Validating every submission would have made that the single account
                # nobody could edit at all, including to correct the owner's name.
                #
                # check_email_typo is shaped as a pydantic validator and raises ValueError; called
                # outside one, that would surface as a 500 rather than as the sentence it wrote.
                try:
                    check_email_typo(normalised)
                except ValueError as typo:
                    raise HTTPException(status_code=400, detail=str(typo)) from typo

                clash = (
                    db.query(User)
                    .filter(func.lower(User.email) == normalised, User.id != user.id)
                    .first()
                )
                if clash is not None:
                    raise HTTPException(status_code=400, detail="Email already exists.")
                user.email = normalised

        return user

    @staticmethod
    def register(request: RegisterRequest, db: Session) -> User:
        course = db.query(Course).filter(Course.id == request.course_id).first()
        if course is None:
            raise HTTPException(
                status_code=404,
                detail="Course not found."
            )

        # GET /schools/ already hides unapproved schools from the picker, but that only shapes the
        # form - this endpoint is public, so a course_id belonging to a pending school can still
        # be posted directly. Without this a student could enrol into a school whose own admin
        # cannot log in yet, and would be left with an account that fails at the login screen for
        # reasons that have nothing to do with them.
        school = db.query(School).filter(School.id == course.school_id).first()
        if school is None or school.status != SCHOOL_APPROVED:
            raise HTTPException(
                status_code=403,
                detail="This school is not accepting registrations yet."
            )

        # Public self-registration always creates a student account - anyone hitting this
        # endpoint directly can't grant themselves instructor/admin access. Those roles are
        # created via school signup (admin) or the /instructors admin-only create endpoint.
        # The student's school is the chosen course's school - "register only to the school
        # you're in" is enforced simply by which course you can pick (see routes/course.py's
        # ?school_id filter on the registration form's dropdown).
        user = AuthService.create_user_account(
            request.email, request.password,
            request.first_name, request.last_name, "student", course.school_id, db,
        )

        # f"STU{user.id:05d}" over a counter table - user IDs are already unique and
        # sequential, so this can't collide without any extra bookkeeping.
        student = Student(
            student_number=f"STU{user.id:05d}",
            user_id=user.id,
            course_id=course.id
        )
        db.add(student)
        db.commit()
        db.refresh(user)

        return user

    @staticmethod
    def login(request: LoginRequest, db: Session):

        # Case-insensitive to match create_user_account's own normalization - see its comment
        # for the real account this broke login for. strip() guards the same sloppy-input
        # pattern (this codebase has real accounts with stray whitespace in other fields).
        user = (
            db.query(User)
            .filter(func.lower(User.email) == request.email.strip().lower())
            .first()
        )

        if user is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password."
            )

        if not verify_password(
                request.password,
                user.password_hash
        ):
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password."
            )

        # A super admin's own school_id is just wherever their account happens to live (see
        # effective_school_id's docstring) - deactivating that school shouldn't lock them out of
        # the platform, since deactivating schools is itself a super-admin-only action. The same
        # reasoning covers approval status: a super admin is who reviews it.
        if user.role.name.lower() != "super_admin":

            # Checked before is_active so a school awaiting review is told it is awaiting review,
            # rather than getting the "deactivated" message meant for one a super admin
            # deliberately shut off. Credentials are verified above either way, so this never
            # reveals whether an email exists at an unapproved school.
            if user.school.status == SCHOOL_PENDING:
                raise HTTPException(
                    status_code=403,
                    detail="Your school's registration is still pending review by the platform "
                           "administrator. You'll be able to sign in once it's approved."
                )

            if user.school.status == SCHOOL_REJECTED:
                note = user.school.review_note
                raise HTTPException(
                    status_code=403,
                    detail=(
                        f"This school's registration was not approved. Reason: {note}"
                        if note else
                        "This school's registration was not approved. Contact the platform "
                        "administrator."
                    )
                )

            if not user.school.is_active:
                raise HTTPException(
                    status_code=403,
                    detail="This school's account has been deactivated. Contact your platform administrator."
                )

        token = create_access_token(
            {
                "sub": user.email
            }
        )

        return {
            "access_token": token,
            "token_type": "bearer"
        }