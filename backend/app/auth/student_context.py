from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import require_student
from app.core.database import get_db
from app.models.student import Student
from app.models.user import User


def get_current_student(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_student),
) -> Student:
    student = db.query(Student).filter(Student.user_id == current_user.id).first()

    if student is None:
        raise HTTPException(
            status_code=404,
            detail="No student profile linked to this account."
        )

    return student
