from pydantic import BaseModel, EmailStr, field_validator

from app.schemas.email_typo import check_email_typo

VALID_ROLE_NAMES = {"student", "instructor", "admin", "super_admin"}


class UserRoleUpdate(BaseModel):
    role_name: str


class PlatformUserCreate(BaseModel):
    """Super admin only - creates a user account of any role, for any school, directly (not
    through school signup or an admin's own instructor/student endpoints, which only ever create
    accounts in the caller's own school)."""
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    role_name: str
    school_id: int

    @field_validator("email")
    @classmethod
    def _reject_mistyped_provider(cls, value: str) -> str:
        check_email_typo(value)
        return value
