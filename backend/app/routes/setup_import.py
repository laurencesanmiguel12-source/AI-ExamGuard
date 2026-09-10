from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin
from app.core.database import get_db
from app.models.user import User
from app.schemas.readiness import SetupReadiness
from app.schemas.setup_import import SetupImportResponse
from app.services.readiness_service import ReadinessService
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


@router.post("/preview", response_model=SetupImportResponse)
async def preview_setup(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """The same import, run and then thrown away, so an admin can see what a file would do.

    Registered after the bare POST above it - a literal path under a router whose own route is
    "" needs no ordering care, but keeping the convention costs nothing.

    Nothing is written. The counts in the response mean "would create", which is why the response
    carries `preview: true` rather than leaving the caller to remember which endpoint it called.
    """
    file_bytes = await file.read()
    return SetupImportService.preview(
        file_bytes, current_user, current_user.school_id, db
    )


@router.get("/readiness", response_model=SetupReadiness)
def setup_readiness(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """What still stands between this school and running an exam.

    Lives under the import router because this is the second half of what the panel asked for
    there - "left floating, then add a workflow to connect them" - but it is not import-specific.
    It is the same question an admin asks at the start of every term, and it walks the program
    flow in order so the first unmet item is genuinely the next thing to do.
    """
    return ReadinessService.report(current_user.school_id, db)
