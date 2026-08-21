from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth.jwt import decode_access_token
from app.core.database import get_db
from app.models.user import User

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    payload = decode_access_token(
        credentials.credentials
    )

    email = payload.get("sub")

    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials."
        )

    user = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found."
        )

    return user


def is_super_admin(user: User) -> bool:
    return user.role.name.lower() == "super_admin"


def effective_school_id(current_user: User) -> int | None:
    """The school id to filter a query by - None means "don't filter, see every school",
    which only ever applies to a super admin. Every school-scoped list/summary query should
    call this instead of reading current_user.school_id directly, or a super admin just sees
    their own home school like a regular admin instead of the whole platform."""
    return None if is_super_admin(current_user) else current_user.school_id


def require_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """Admin OR super admin - a super admin can do everything a school admin can, for any
    school. Routes/services that need the caller's school scope should use effective_school_id
    (or check is_super_admin directly) rather than current_user.school_id, since a super admin's
    own school_id is just wherever their account happens to live, not a real scope restriction."""

    role = current_user.role.name.lower()
    if role not in ("admin", "super_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required."
        )

    return current_user


def require_super_admin(
    current_user: User = Depends(get_current_user)
) -> User:

    if not is_super_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required."
        )

    return current_user


def require_instructor(
    current_user: User = Depends(get_current_user)
) -> User:

    if current_user.role.name.lower() != "instructor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Instructor access required."
        )

    return current_user


def require_student(
    current_user: User = Depends(get_current_user)
) -> User:

    if current_user.role.name.lower() != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Student access required."
        )

    return current_user