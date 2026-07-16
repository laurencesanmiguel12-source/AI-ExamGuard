from fastapi import APIRouter
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.schemas.auth import RegisterRequest
from app.schemas.user import UserResponse
from app.auth.security import hash_password
from app.auth.service import AuthService

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

@router.post(
    "/register",
    response_model=UserResponse
)
def register(
    request: RegisterRequest,
    db: Session = Depends(get_db)
):
    return AuthService.register(request, db)