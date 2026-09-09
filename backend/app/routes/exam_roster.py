from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.ownership import require_exam_owner
from app.core.database import get_db
from app.models.exam import Exam
from app.schemas.exam_roster import ExamRosterCreate, ExamRosterWithStudentResponse
from app.schemas.student import StudentResponse
from app.services.exam_roster_service import ExamRosterService
from app.services.exam_service import ExamService

router = APIRouter(prefix="/exams", tags=["Exam Roster"])


@router.get(
    "/{exam_id}/roster",
    response_model=list[ExamRosterWithStudentResponse]
)
def list_exam_roster(
    db: Session = Depends(get_db),
    exam: Exam = Depends(require_exam_owner)
):
    return ExamRosterService.get_all_for_exam(exam, db)


# Literal path registered before the {param} routes below it - main.py's route-ordering rule.
@router.get("/{exam_id}/roster/source")
def exam_roster_source(
    db: Session = Depends(get_db),
    exam: Exam = Depends(require_exam_owner)
):
    """Where this exam's roster comes from, and whether it currently admits anybody.

    The roster screen needs this to tell two visually identical situations apart: an exam
    inheriting a healthy class list, and one pointing at a section with nobody enrolled. The
    second admits no students at all, and without this it looks exactly like a correctly
    configured exam right up until nobody can start it.
    """
    return ExamService.roster_source(exam, db)


@router.get(
    "/{exam_id}/roster/available",
    response_model=list[StudentResponse]
)
def list_available_roster_students(
    db: Session = Depends(get_db),
    exam: Exam = Depends(require_exam_owner)
):
    return ExamRosterService.get_available_students(exam, db)


@router.post(
    "/{exam_id}/roster",
    response_model=ExamRosterWithStudentResponse
)
def add_exam_roster_student(
    request: ExamRosterCreate,
    db: Session = Depends(get_db),
    exam: Exam = Depends(require_exam_owner)
):
    return ExamRosterService.add_student(exam, request, db)


# Declared as a literal sub-path, not a concern for the /{student_id} param route below since
# they're different HTTP methods (POST vs DELETE) - same defensive habit as this project's other
# literal-before-param route ordering, just not actually at risk here.
@router.post("/{exam_id}/roster/bulk-add")
def bulk_add_exam_roster_students(
    db: Session = Depends(get_db),
    exam: Exam = Depends(require_exam_owner)
):
    return ExamRosterService.add_all_available(exam, db)


@router.delete("/{exam_id}/roster/{student_id}")
def remove_exam_roster_student(
    student_id: int,
    db: Session = Depends(get_db),
    exam: Exam = Depends(require_exam_owner)
):
    return ExamRosterService.remove_student(exam, student_id, db)
