from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.auth.security import hash_password
from app.models.course import Course
from app.models.role import Role
from app.models.student import Student
from app.models.user import User
from app.schemas.auth import RegisterRequest
from app.schemas.auth import LoginRequest
from app.auth.jwt import create_access_token
from app.auth.security import verify_password


class AuthService:

    @staticmethod
    def create_user_account(
        username: str,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        role_name: str,
        db: Session,
    ) -> User:
        """Shared by public self-registration (always role_name="student") and the admin-only
        instructor/student creation endpoints - same duplicate-checks + role lookup + User row
        every account needs, just with the role and the linked profile row differing. Leaves the
        transaction open (flush, not commit) so the caller can add its profile row (Student/
        Instructor) and commit both together."""

        existing_username = (
            db.query(User)
            .filter(User.username == username)
            .first()
        )

        if existing_username:
            raise HTTPException(
                status_code=400,
                detail="Username already exists."
            )

        existing_email = (
            db.query(User)
            .filter(User.email == email)
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
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            password_hash=hash_password(password),
            role_id=role.id,
            is_active=True
        )
        db.add(user)
        db.flush()  # assigns user.id without committing, for the caller's profile row

        return user

    @staticmethod
    def register(request: RegisterRequest, db: Session) -> User:
        course = db.query(Course).filter(Course.id == request.course_id).first()
        if course is None:
            raise HTTPException(
                status_code=404,
                detail="Course not found."
            )

        # Public self-registration always creates a student account - anyone hitting this
        # endpoint directly can't grant themselves instructor/admin access. Those roles are
        # created by an admin via the /instructors or /students admin-only create endpoints.
        user = AuthService.create_user_account(
            request.username, request.email, request.password,
            request.first_name, request.last_name, "student", db,
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

        user = (
            db.query(User)
            .filter(User.email == request.email)
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

        token = create_access_token(
            {
                "sub": user.email
            }
        )

        return {
            "access_token": token,
            "token_type": "bearer"
        }