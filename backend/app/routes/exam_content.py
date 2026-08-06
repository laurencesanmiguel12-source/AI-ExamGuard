from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.ownership import require_exam_owner
from app.core.database import get_db
from app.models.exam import Exam
from app.models.exam_session import ExamSession, GRADED_STATUSES
from app.models.instructor import Instructor
from app.models.student import Student
from app.models.user import User
from app.schemas.choice import ChoiceCreate, ChoiceResponse, ChoiceUpdate
from app.schemas.csv_import import CSVImportResponse
from app.schemas.question import (
    QuestionCreate,
    QuestionPublicResponse,
    QuestionUpdate,
    QuestionWithChoicesResponse,
)
from app.services.choice_service import ChoiceService
from app.services.csv_import_service import CSVImportService
from app.services.exam_service import ExamService
from app.services.question_service import QuestionService

router = APIRouter(prefix="/exams", tags=["Exam Content"])


# No static response_model here on purpose - instructors/admins get the full
# QuestionWithChoicesResponse shape (with is_correct, needed to manage the exam), students get
# QuestionPublicResponse (answer key stripped). Explicitly constructing the right Pydantic model
# per branch below guarantees the shape actually sent over the wire, rather than relying on a
# single declared response_model to filter it after the fact.
@router.get("/{exam_id}/questions")
def list_exam_questions(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> list[QuestionWithChoicesResponse] | list[QuestionPublicResponse]:
    exam = db.query(Exam).filter(Exam.id == exam_id).first()

    if exam is None:
        raise HTTPException(status_code=404, detail="Exam not found.")

    role = current_user.role.name.lower()

    if role == "admin":
        return QuestionService.get_all_for_exam(exam, db)

    if role == "instructor":
        instructor = db.query(Instructor).filter(Instructor.user_id == current_user.id).first()
        if instructor is not None and exam.instructor_id == instructor.id:
            return QuestionService.get_all_for_exam(exam, db)
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to view this exam's questions."
        )

    if role == "student":
        student = db.query(Student).filter(Student.user_id == current_user.id).first()
        if student is None or not ExamService.is_student_eligible(student, exam, db):
            raise HTTPException(
                status_code=403,
                detail="This exam is not available for your course."
            )

        questions = QuestionService.get_all_for_exam(exam, db)

        # Full answer key only after the student has actually submitted THIS exam - ResultDetail.jsx
        # relies on is_correct being present to highlight the right answer during post-exam review,
        # and by that point showing it can no longer help them cheat on it. Anyone still taking it
        # (or who hasn't started yet) gets the redacted shape.
        has_submitted = (
            db.query(ExamSession)
            .filter(
                ExamSession.student_id == student.id,
                ExamSession.exam_id == exam.id,
                ExamSession.status.in_(GRADED_STATUSES),
            )
            .first()
            is not None
        )
        if has_submitted:
            return questions
        return [QuestionPublicResponse.model_validate(q) for q in questions]

    raise HTTPException(
        status_code=403,
        detail="You do not have permission to view this exam's questions."
    )


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
