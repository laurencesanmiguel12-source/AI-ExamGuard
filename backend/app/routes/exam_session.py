from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.exam_session import (
    ExamSessionCreate,
    ExamSessionResponse,
    ExamSessionUpdate,
)
from app.services.exam_session_service import ExamSessionService

router = APIRouter(
    prefix="/exam-sessions",
    tags=["Exam Sessions"]
)


@router.post(
    "/start",
    response_model=ExamSessionResponse
)
def start_exam(
    request: ExamSessionCreate,
    db: Session = Depends(get_db)
):
    return ExamSessionService.start_exam(request, db)


@router.get(
    "",
    response_model=list[ExamSessionResponse]
)
def get_sessions(
    db: Session = Depends(get_db)
):
    return ExamSessionService.get_all(db)


@router.get(
    "/{session_id}",
    response_model=ExamSessionResponse
)
def get_session(
    session_id: int,
    db: Session = Depends(get_db)
):
    return ExamSessionService.get_by_id(session_id, db)


@router.put(
    "/submit/{session_id}",
    response_model=ExamSessionResponse
)
def submit_exam(
    session_id: int,
    db: Session = Depends(get_db)
):
    return ExamSessionService.submit_exam(session_id, db)


@router.put(
    "/{session_id}",
    response_model=ExamSessionResponse
)
def update_session(
    session_id: int,
    request: ExamSessionUpdate,
    db: Session = Depends(get_db)
):
    return ExamSessionService.update(
        session_id,
        request,
        db
    )


@router.delete("/{session_id}")
def delete_session(
    session_id: int,
    db: Session = Depends(get_db)
):
    return ExamSessionService.delete(
        session_id,
        db
    )