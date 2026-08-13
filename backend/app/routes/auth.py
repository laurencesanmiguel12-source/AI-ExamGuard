from fastapi import APIRouter, Request
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rate_limit import limiter
from app.models.user import User
from app.schemas.auth import RegisterRequest
from app.schemas.user import UserResponse
from app.auth.security import hash_password
from app.auth.service import AuthService
from app.schemas.auth import LoginRequest, TokenResponse
from app.auth.dependencies import get_current_user



router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

# Both unauthenticated by nature (that's the point) and public since going live - rate-limited
# per IP against signup spam / credential-stuffing. Hardcoded, documented values, same discipline
# as EVIDENCE_RETENTION_DAYS elsewhere - not empirically tuned, easy to adjust if real traffic
# shows they're too tight/loose.
@router.post(
    "/register",
    response_model=UserResponse
)
@limiter.limit("5/minute")
def register(
    request: Request,
    body: RegisterRequest,
    db: Session = Depends(get_db)
):
    return AuthService.register(body, db)

@router.post(
    "/login",
    response_model=TokenResponse
)
@limiter.limit("10/minute")
def login(
    request: Request,
    body: LoginRequest,
    db: Session = Depends(get_db)
):
    return AuthService.login(body, db)

@router.get(
    "/me",
    response_model=UserResponse
)
def get_me(
    current_user: User = Depends(get_current_user)
):
    return current_user