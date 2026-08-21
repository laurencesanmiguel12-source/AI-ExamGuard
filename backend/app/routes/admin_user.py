from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import require_super_admin
from app.core.database import get_db
from app.models.user import User
from app.schemas.admin_user import PlatformUserCreate, UserRoleUpdate
from app.schemas.user import UserResponse
from app.services.admin_user_service import AdminUserService

# Super admin only, every route - platform-wide account management (see any user regardless of
# school, promote/demote roles, create admin/super_admin accounts directly). Registered under
# /admin/users, not /students or /instructors, since this is explicitly NOT school-scoped the way
# those are.
router = APIRouter(
    prefix="/admin/users",
    tags=["Admin"]
)


@router.get(
    "/",
    response_model=list[UserResponse]
)
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    return AdminUserService.get_all(db)


@router.put(
    "/{user_id}/role",
    response_model=UserResponse
)
def update_user_role(
    user_id: int,
    request: UserRoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    return AdminUserService.update_role(user_id, request.role_name, current_user, db)


@router.post(
    "/",
    response_model=UserResponse
)
def create_platform_user(
    request: PlatformUserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    return AdminUserService.create(request, db)
