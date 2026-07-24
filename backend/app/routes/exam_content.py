from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.ownership import require_exam_owner
from app.core.database import get_db
from app.models.exam import Exam
from app.models.user import User
from app.schemas.choice import ChoiceCreate, ChoiceResponse, ChoiceUpdate
from app.schemas.csv_import import CSVImportResponse
from app.schemas.question import (
    QuestionCreate,
    QuestionUpdate,
    QuestionWithChoicesResponse,
)
from app.services.choice_service import ChoiceService
from app.services.csv_import_service import CSVImportService
from app.services.question_service import QuestionService

router = APIRouter(prefix="/exams", tags=["Exam Content"])


@router.get(
    "/{exam_id}/questions",
    response_model=list[QuestionWithChoicesResponse]
)
def list_exam_questions(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    exam = db.query(Exam).filter(Exam.id == exam_id).first()

    if exam is None:
        raise HTTPException(status_code=404, detail="Exam not found.")

    return QuestionService.get_all_for_exam(exam, db)


# Declared before the create-question route (same defensive habit as the import route below):
# a same-method literal path added later at this depth (e.g. a CSV template download) would
# otherwise risk being swallowed by a param route registered first.
@router.post(
    "/{exam_id}/questions/import",
    response_model=CSVImportResponse
)
async def import_exam_questions(
    exam_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    exam: Exam = Depends(require_exam_owner)
):
    file_bytes = await file.read()
    return CSVImportService.import_questions(exam, file_bytes, db)


@router.post(
    "/{exam_id}/questions",
    response_model=QuestionWithChoicesResponse
)
def create_exam_question(
    exam_id: int,
    request: QuestionCreate,
    db: Session = Depends(get_db),
    exam: Exam = Depends(require_exam_owner)
):
    return QuestionService.create(exam, request, db)


@router.put(
    "/{exam_id}/questions/{question_id}",
    response_model=QuestionWithChoicesResponse
)
def update_exam_question(
    exam_id: int,
    question_id: int,
    request: QuestionUpdate,
    db: Session = Depends(get_db),
    exam: Exam = Depends(require_exam_owner)
):
    return QuestionService.update(exam, question_id, request, db)


@router.delete(
    "/{exam_id}/questions/{question_id}"
)
def delete_exam_question(
    exam_id: int,
    question_id: int,
    db: Session = Depends(get_db),
    exam: Exam = Depends(require_exam_owner)
):
    return QuestionService.delete(exam, question_id, db)


@router.post(
    "/{exam_id}/questions/{question_id}/choices",
    response_model=ChoiceResponse
)
def create_exam_choice(
    exam_id: int,
    question_id: int,
    request: ChoiceCreate,
    db: Session = Depends(get_db),
    exam: Exam = Depends(require_exam_owner)
):
    question = QuestionService.get_owned(exam, question_id, db)
    return ChoiceService.create(question, request, db)


@router.put(
    "/{exam_id}/questions/{question_id}/choices/{choice_id}",
    response_model=ChoiceResponse
)
def update_exam_choice(
    exam_id: int,
    question_id: int,
    choice_id: int,
    request: ChoiceUpdate,
    db: Session = Depends(get_db),
    exam: Exam = Depends(require_exam_owner)
):
    question = QuestionService.get_owned(exam, question_id, db)
    return ChoiceService.update(question, choice_id, request, db)


@router.delete(
    "/{exam_id}/questions/{question_id}/choices/{choice_id}"
)
def delete_exam_choice(
    exam_id: int,
    question_id: int,
    choice_id: int,
    db: Session = Depends(get_db),
    exam: Exam = Depends(require_exam_owner)
):
    question = QuestionService.get_owned(exam, question_id, db)
    return ChoiceService.delete(question, choice_id, db)
