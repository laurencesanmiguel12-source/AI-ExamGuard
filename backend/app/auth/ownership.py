from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import is_super_admin, require_admin, require_instructor
from app.core.database import get_db
from app.models.course import Course
from app.models.exam import Exam
from app.models.instructor import Instructor
from app.models.subject import Subject
from app.models.user import User


def require_exam_owner(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_instructor),
) -> Exam:
    exam = db.query(Exam).filter(Exam.id == exam_id).first()

    if exam is None:
        raise HTTPException(status_code=404, detail="Exam not found.")

    if current_user.role.name.lower() in ("admin", "super_admin"):
        exam_school_id = (
            db.query(Course.school_id)
            .join(Subject, Subject.course_id == Course.id)
            .filter(Subject.id == exam.subject_id)
            .scalar()
        )
        if not is_super_admin(current_user) and exam_school_id != current_user.school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to manage this exam's content."
            )
        return exam

    instructor = db.query(Instructor).filter(Instructor.user_id == current_user.id).first()

    if instructor is None or exam.instructor_id != instructor.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to manage this exam's content."
        )

    return exam


def require_course_owner(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> Course:
    """Multi-tenancy ownership check: before this, ANY admin could edit/delete ANY course - there
    was only ever one admin so it never surfaced. Same shape as require_exam_owner, just keyed on
    school instead of a direct instructor_id column."""
    course = db.query(Course).filter(Course.id == course_id).first()

    if course is None:
        raise HTTPException(status_code=404, detail="Course not found.")

    if not is_super_admin(current_user) and course.school_id != current_user.school_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to manage this course."
        )

    return course
