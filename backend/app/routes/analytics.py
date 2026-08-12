from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin
from app.auth.instructor_context import get_current_instructor
from app.core.database import get_db
from app.models.instructor import Instructor
from app.models.user import User
from app.schemas.analytics import InstructorAnalytics, SchoolAnalytics
from app.services.analytics_service import AnalyticsService

router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"]
)


@router.get(
    "/instructor",
    response_model=InstructorAnalytics
)
def get_instructor_analytics(
    db: Session = Depends(get_db),
    instructor: Instructor = Depends(get_current_instructor)
):
    return AnalyticsService.get_instructor_summary(instructor, db)


@router.get(
    "/school",
    response_model=SchoolAnalytics
)
def get_school_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    return AnalyticsService.get_school_summary(current_user.school_id, db)
