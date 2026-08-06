from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin
from app.auth.ownership import require_course_owner
from app.core.database import get_db
from app.models.course import Course
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


# Public (no auth) - the self-registration form needs to populate its course dropdown before the
# visitor has an account. Course code/name is non-sensitive catalog data, but the list is always
# scoped to one school - a student registering (or an authenticated admin/instructor's own pages)
# always knows which school_id they mean, so this stays a required param rather than ever
# returning every school's catalog at once.
@router.get(
    "/",
    response_model=list[CourseResponse]
)
def get_courses(
    school_id: int,
    db: Session = Depends(get_db)
):
    return CourseService.get_all(db, school_id)


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
    return CourseService.create(request, current_user.school_id, db)


@router.put(
    "/{course_id}",
    response_model=CourseResponse
)
def update_course(
    course_id: int,
    request: CourseUpdate,
    db: Session = Depends(get_db),
    course: Course = Depends(require_course_owner)
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
    course: Course = Depends(require_course_owner)
):
    return CourseService.delete(course_id, db)