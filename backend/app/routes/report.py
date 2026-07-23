from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import require_instructor
from app.core.database import get_db
from app.models.user import User
from app.schemas.report import ExamReport
from app.services.report_service import ReportService

router = APIRouter(
    prefix="/exams",
    tags=["Reports"]
)


@router.get(
    "/{exam_id}/report",
    response_model=ExamReport
)
def get_exam_report(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_instructor)
):
    return ReportService.get_exam_report(exam_id, db)
