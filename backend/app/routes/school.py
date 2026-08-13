from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rate_limit import limiter
from app.schemas.school import SchoolRegisterRequest, SchoolResponse
from app.services.school_service import SchoolService

router = APIRouter(
    prefix="/schools",
    tags=["Schools"]
)


# Public (no auth) - the registration form's school picker needs to work before the visitor has
# an account, same treatment GET /courses already got.
@router.get(
    "/",
    response_model=list[SchoolResponse]
)
def get_schools(
    db: Session = Depends(get_db)
):
    return SchoolService.get_all(db)


# Public (no auth) - self-service school signup, same pattern as public student registration.
# This is the first-ever way to create an admin account in this codebase - tightest rate limit of
# the three public signup/login endpoints, since a new school is a rare, deliberate action, not
# something a legitimate user does repeatedly.
@router.post(
    "/register",
    response_model=SchoolResponse
)
@limiter.limit("3/hour")
def register_school(
    request: Request,
    body: SchoolRegisterRequest,
    db: Session = Depends(get_db)
):
    return SchoolService.register(body, db)
