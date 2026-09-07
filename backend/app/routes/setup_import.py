from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin
from app.core.database import get_db
from app.models.user import User
from app.schemas.setup_import import SetupImportResponse
from app.services.setup_import_service import SetupImportService

router = APIRouter(prefix="/admin/setup-import", tags=["Admin"])


@router.post("", response_model=SetupImportResponse)
async def import_setup(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Bulk-create courses, subjects and instructors from one CSV.

    Admin-only, and always into the caller's OWN school: school_id comes from the session, never
    from the file, so a sheet cannot create records somewhere else.

    Deliberately current_user.school_id rather than effective_school_id(). That helper returns
    None for a super admin, meaning "do not filter, read every school" - correct for listing,
    meaningless for creating, since there is no such thing as writing a course into every school
    at once. A super admin importing therefore fills in their own home school, which is
    predictable; scoping a write by a read helper would have created rows with a null school.
    """
    file_bytes = await file.read()
    return SetupImportService.import_setup(
        file_bytes, current_user, current_user.school_id, db
    )
