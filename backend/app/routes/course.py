from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin
from app.core.database import get_db
from app.models.user import User
from app.schemas.course import (
    CourseCreate,
    CourseUpdate,
    CourseResponse,
)
from app.services.course_service import CourseService

router = APIRouter(
    prefix="/courses",
    tags=["Courses"]
)


# Public (no auth) - the self-registration form needs to populate its course dropdown before
# the visitor has an account. Course code/name is non-sensitive catalog data.
@router.get(
    "/",
    response_model=list[CourseResponse]
)
def get_courses(
    db: Session = Depends(get_db)
):
    return CourseService.get_all(db)


@router.get(
    "/{course_id}",
    response_model=CourseResponse
)
def get_course(
    course_id: int,
    db: Session = Depends(get_db)
):
    return CourseService.get_by_id(course_id, db)


@router.post(
    "/",
    response_model=CourseResponse
)
def create_course(
    request: CourseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    return CourseService.create(request, db)


@router.put(
    "/{course_id}",
    response_model=CourseResponse
)
def update_course(
    course_id: int,
    request: CourseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    return CourseService.update(
        course_id,
        request,
        db
    )


@router.delete(
    "/{course_id}"
)
def delete_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    return CourseService.delete(course_id, db)