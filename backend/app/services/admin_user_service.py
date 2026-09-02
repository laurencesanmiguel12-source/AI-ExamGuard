from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.auth.service import AuthService
from app.models.role import Role
from app.models.school import School
from app.models.user import User
from app.schemas.admin_user import VALID_ROLE_NAMES, PlatformUserCreate


class AdminUserService:

    @staticmethod
    def get_all(db: Session):
        # Deliberately unscoped - this is the one listing in the codebase that's SUPPOSED to
        # span every school, gated by require_super_admin at the route rather than a school_id
        # filter here (there's no "current school" to filter by for a platform-wide user list).
        return db.query(User).all()

    @staticmethod
    def update_role(user_id: int, role_name: str, current_user: User, db: Session) -> User:
        if role_name not in VALID_ROLE_NAMES:
            raise HTTPException(
                status_code=400,
                detail=f"role_name must be one of {sorted(VALID_ROLE_NAMES)}."
            )

        if user_id == current_user.id:
            # Purely to prevent a fat-fingered self-demotion from locking the only super admin
            # out of the one endpoint that could undo it - a deliberate self-demotion is still
            # possible by having a different super admin do it.
            raise HTTPException(
                status_code=400,
                detail="Cannot change your own role - have another super admin do it."
            )

        user = db.query(User).filter(User.id == user_id).first()
        if user is None:
            raise HTTPException(status_code=404, detail="User not found.")

        role = db.query(Role).filter(Role.name == role_name).first()
        if role is None:
            raise HTTPException(status_code=500, detail=f"{role_name} role is not configured.")

        # A school with zero admins cannot be administered at all: Courses/Subjects/Students/
        # Instructors are all require_admin, and there is no super-admin UI in front of those
        # routes. This is not hypothetical - EARIST (school 11) sat in exactly that state in
        # production, and recovering it needed a hand-run script because the one endpoint that
        # creates admins is itself super-admin-only. Note this blocks promotion to super_admin
        # too: a super admin is not school-scoped, so it does not backfill the school's admin
        # slot. Promote a replacement first, then move this account.
        if role_name != "admin" and user.role.name.lower() == "admin":
            other_admins = (
                db.query(User)
                .join(Role, User.role_id == Role.id)
                .filter(
                    User.school_id == user.school_id,
                    Role.name.ilike("admin"),
                    User.id != user.id,
                )
                .count()
            )
            if other_admins == 0:
                raise HTTPException(
                    status_code=400,
                    detail="This is the only admin of their school - give the school another "
                           "admin before changing this account's role."
                )

        # Deliberately NOT creating/removing the linked Student/Instructor profile row - changing
        # role_id alone is enough to grant/revoke the new role's access, but a former
        # student/instructor's profile row (course enrollment, employee number, face model, etc.)
        # is left in place. Re-promoting them back later restores that context intact rather than
        # losing it; a genuinely orphaned profile row is a acceptable, disclosed side effect of
        # this narrow "change access level" action, not a full account-type migration.
        user.role_id = role.id
        db.commit()
        db.refresh(user)

        return user

    @staticmethod
    def create(request: PlatformUserCreate, db: Session) -> User:
        if request.role_name not in VALID_ROLE_NAMES:
            raise HTTPException(
                status_code=400,
                detail=f"role_name must be one of {sorted(VALID_ROLE_NAMES)}."
            )

        # student/instructor both need a required linked profile row this endpoint has no way to
        # fill in (course_id, employee_number) - checked before create_user_account runs at all,
        # not after, so nothing gets flushed for a request that's going to be rejected anyway.
        if request.role_name in ("student", "instructor"):
            raise HTTPException(
                status_code=400,
                detail=f"Use an admin's own POST /{request.role_name}s to create {request.role_name} accounts - "
                       f"this endpoint is for admin/super_admin only, which need no linked profile row."
            )

        school = db.query(School).filter(School.id == request.school_id).first()
        if school is None:
            raise HTTPException(status_code=404, detail="School not found.")

        user = AuthService.create_user_account(
            request.email, request.password,
            request.first_name, request.last_name, request.role_name, request.school_id, db,
        )

        db.commit()
        db.refresh(user)

        return user
