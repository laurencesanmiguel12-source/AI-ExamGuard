from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import require_instructor
from app.core.database import get_db
from app.models.instructor import Instructor
from app.models.user import User


def get_current_instructor(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_instructor),
) -> Instructor:
    instructor = db.query(Instructor).filter(Instructor.user_id == current_user.id).first()

    if instructor is None:
        raise HTTPException(
            status_code=404,
            detail="No instructor profile linked to this account."
        )

    return instructor
