from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.auth.security import hash_password
from app.models.user import User
from app.schemas.auth import RegisterRequest
from app.schemas.auth import LoginRequest
from app.auth.jwt import create_access_token
from app.auth.security import verify_password


class AuthService:

    @staticmethod
    def register(request: RegisterRequest, db: Session) -> User:
        existing_username = (
            db.query(User)
            .filter(User.username == request.username)
            .first()
        )

        if existing_username:
            raise HTTPException(
                status_code=400,
                detail="Username already exists."
            )

        existing_email = (
            db.query(User)
            .filter(User.email == request.email)
            .first()
        )

        if existing_email:
            raise HTTPException(
                status_code=400,
                detail="Email already exists."
            )

        hashed_password = hash_password(request.password)

        user = User(
            username=request.username,
            email=request.email,
            first_name=request.first_name,
            last_name=request.last_name,
            password_hash=hashed_password,
            role_id=request.role_id,
            is_active=True
        )
        db.add(user)
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