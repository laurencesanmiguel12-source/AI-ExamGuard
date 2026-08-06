from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin
from app.core.database import get_db
from app.models.instructor import Instructor
from app.models.user import User
from app.schemas.instructor_subject import (
    InstructorSubjectCreate,
    InstructorSubjectWithSubjectResponse,
)
from app.services.instructor_service import InstructorService
from app.services.instructor_subject_service import InstructorSubjectService

router = APIRouter(prefix="/instructors/{instructor_id}/subjects", tags=["Instructor Subject Assignments"])


@router.get(
    "/",
    response_model=list[InstructorSubjectWithSubjectResponse]
)
def list_instructor_subjects(
    instructor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    instructor = InstructorService.get_by_id(instructor_id, current_user, db)
    return InstructorSubjectService.get_all_for_instructor(instructor, db)


@router.post(
    "/",
    response_model=InstructorSubjectWithSubjectResponse
)
def assign_instructor_subject(
    instructor_id: int,
    request: InstructorSubjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    instructor = InstructorService.get_by_id(instructor_id, current_user, db)
    return InstructorSubjectService.assign(instructor, request, db)


@router.delete("/{subject_id}")
def unassign_instructor_subject(
    instructor_id: int,
    subject_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    instructor: Instructor = InstructorService.get_by_id(instructor_id, current_user, db)
    return InstructorSubjectService.unassign(instructor, subject_id, db)
