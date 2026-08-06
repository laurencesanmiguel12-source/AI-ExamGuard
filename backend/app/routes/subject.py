from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_admin
from app.core.database import get_db
from app.models.user import User
from app.schemas.subject import (
    SubjectCreate,
    SubjectUpdate,
    SubjectResponse,
)
from app.services.subject_service import SubjectService

router = APIRouter(
    prefix="/subjects",
    tags=["Subjects"]
)


@router.get(
    "/",
    response_model=list[SubjectResponse]
)
def get_subjects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return SubjectService.get_all(current_user, db)


@router.get(
    "/{subject_id}",
    response_model=SubjectResponse
)
def get_subject(
    subject_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return SubjectService.get_by_id(subject_id, current_user, db)


@router.post(
    "/",
    response_model=SubjectResponse
)
def create_subject(
    request: SubjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    return SubjectService.create(request, current_user, db)


@router.put(
    "/{subject_id}",
    response_model=SubjectResponse
)
def update_subject(
    subject_id: int,
    request: SubjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    return SubjectService.update(
        subject_id,
        request,
        current_user,
        db
    )


@router.delete(
    "/{subject_id}"
)
def delete_subject(
    subject_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    return SubjectService.delete(subject_id, current_user, db)