from pydantic import BaseModel, EmailStr

VALID_ROLE_NAMES = {"student", "instructor", "admin", "super_admin"}


class UserRoleUpdate(BaseModel):
    role_name: str


class PlatformUserCreate(BaseModel):
    """Super admin only - creates a user account of any role, for any school, directly (not
    through school signup or an admin's own instructor/student endpoints, which only ever create
    accounts in the caller's own school)."""
    username: str
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    role_name: str
    school_id: int
