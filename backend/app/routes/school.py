from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.auth.dependencies import require_super_admin
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.models.user import User
from app.schemas.school import (
    SchoolPublicStatusResponse,
    SchoolRegisterRequest,
    SchoolResponse,
    SchoolReviewRequest,
    SchoolUpdate,
)
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


# Super admin only - the review queue. Declared before /{school_id} below: a literal path
# registered after an overlapping param route gets swallowed by it (see CLAUDE.md).
@router.get(
    "/review",
    response_model=list[SchoolResponse]
)
def list_schools_for_review(
    status: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """Unlike the public GET /schools/, this lists every school whatever its status - it is the
    only way a pending signup is visible at all. ?status=pending for just the queue."""
    return SchoolService.get_all_for_review(db, status)


# Public (no auth), and deliberately resolves schools of ANY status - the login page for a school
# that is still pending has to be able to say so to the person who registered it, rather than
# behaving as though the school does not exist. Returns name/status only.
@router.get(
    "/slug/{slug}",
    response_model=SchoolPublicStatusResponse
)
def get_school_by_slug(
    slug: str,
    db: Session = Depends(get_db)
):
    return SchoolService.get_public_by_slug(slug, db)


# Super admin only - approve or reject a pending signup. Approving is what lets that school's
# founding admin (created at signup time) finally log in.
@router.put(
    "/{school_id}/review",
    response_model=SchoolResponse
)
def review_school(
    school_id: int,
    body: SchoolReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    return SchoolService.review(school_id, body, current_user, db)


# Super admin only - edit a school's identity, or deactivate/reactivate it (blocks login for
# every one of its users without deleting their data - see School.is_active and
# AuthService.login).
@router.put(
    "/{school_id}",
    response_model=SchoolResponse
)
def update_school(
    school_id: int,
    body: SchoolUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    return SchoolService.update(school_id, body, db)
