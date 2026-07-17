from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import (
    get_current_user,
    require_admin
)
from app.core.database import get_db
from app.models.user import User
from app.schemas.instructor import (
    InstructorCreate,
    InstructorUpdate,
    InstructorResponse
)
from app.services.instructor_service import InstructorService

router = APIRouter(
    prefix="/instructors",
    tags=["Instructors"]
)


@router.get(
    "/",
    response_model=list[InstructorResponse]
)
def get_instructors(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return InstructorService.get_all(db)


@router.get(
    "/{instructor_id}",
    response_model=InstructorResponse
)
def get_instructor(
    instructor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return InstructorService.get_by_id(
        instructor_id,
        db
    )


@router.post(
    "/",
    response_model=InstructorResponse
)
def create_instructor(
    request: InstructorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    return InstructorService.create(
        request,
        db
    )


@router.put(
    "/{instructor_id}",
    response_model=InstructorResponse
)
def update_instructor(
    instructor_id: int,
    request: InstructorUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    return InstructorService.update(
        instructor_id,
        request,
        db
    )


@router.delete(
    "/{instructor_id}"
)
def delete_instructor(
    instructor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    return InstructorService.delete(
        instructor_id,
        db
    )