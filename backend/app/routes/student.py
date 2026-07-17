from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_admin
from app.core.database import get_db
from app.models.user import User
from app.schemas.student import (
    StudentCreate,
    StudentUpdate,
    StudentResponse
)
from app.services.student_service import StudentService

router = APIRouter(
    prefix="/students",
    tags=["Students"]
)


@router.get(
    "/",
    response_model=list[StudentResponse]
)
def get_students(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return StudentService.get_all(db)


@router.get(
    "/{student_id}",
    response_model=StudentResponse
)
def get_student(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return StudentService.get_by_id(student_id, db)


@router.post(
    "/",
    response_model=StudentResponse
)
def create_student(
    request: StudentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    return StudentService.create(request, db)


@router.put(
    "/{student_id}",
    response_model=StudentResponse
)
def update_student(
    student_id: int,
    request: StudentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    return StudentService.update(
        student_id,
        request,
        db
    )


@router.delete(
    "/{student_id}"
)
def delete_student(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    return StudentService.delete(student_id, db)