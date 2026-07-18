from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.question import (
    QuestionCreate,
    QuestionUpdate,
    QuestionResponse,
)
from app.services.question_service import QuestionService

router = APIRouter(
    prefix="/questions",
    tags=["Questions"]
)


@router.post(
    "",
    response_model=QuestionResponse
)
def create_question(
    request: QuestionCreate,
    db: Session = Depends(get_db)
):
    return QuestionService.create(request, db)


@router.get(
    "",
    response_model=list[QuestionResponse]
)
def get_questions(
    db: Session = Depends(get_db)
):
    return QuestionService.get_all(db)


@router.get(
    "/{question_id}",
    response_model=QuestionResponse
)
def get_question(
    question_id: int,
    db: Session = Depends(get_db)
):
    return QuestionService.get_by_id(question_id, db)


@router.put(
    "/{question_id}",
    response_model=QuestionResponse
)
def update_question(
    question_id: int,
    request: QuestionUpdate,
    db: Session = Depends(get_db)
):
    return QuestionService.update(question_id, request, db)


@router.delete(
    "/{question_id}"
)
def delete_question(
    question_id: int,
    db: Session = Depends(get_db)
):
    return QuestionService.delete(question_id, db)