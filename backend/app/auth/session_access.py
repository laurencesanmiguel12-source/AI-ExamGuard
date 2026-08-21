from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.student_context import get_current_student
from app.core.database import get_db
from app.models.course import Course
from app.models.exam import Exam
from app.models.exam_session import ExamSession
from app.models.instructor import Instructor
from app.models.student import Student
from app.models.subject import Subject
from app.models.user import User
from app.models.violation import Violation


def require_own_student(
    student_id: int,
    student: Student = Depends(get_current_student),
) -> Student:
    if student.id != student_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only manage your own student profile."
        )
    return student


def require_session_owner_student(
    session_id: int,
    db: Session = Depends(get_db),
    student: Student = Depends(get_current_student),
) -> ExamSession:
    session = db.query(ExamSession).filter(ExamSession.id == session_id).first()

    if session is None:
        raise HTTPException(status_code=404, detail="Exam session not found.")

    if session.student_id != student.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This exam session does not belong to you."
        )

    return session


def _owning_instructor_matches(session: ExamSession, current_user: User, db: Session) -> bool:
    exam = db.query(Exam).filter(Exam.id == session.exam_id).first()
    instructor = (
        db.query(Instructor)
        .filter(Instructor.user_id == current_user.id)
        .first()
    )
    return exam is not None and instructor is not None and exam.instructor_id == instructor.id


def _session_school_id(session: ExamSession, db: Session) -> int | None:
    """Same join path as ExamSessionService.get_all's admin branch and
    exam_content.py's list_exam_questions - the one other place in the codebase that already
    got this right. An "admin" role check with no accompanying school comparison is exactly
    the cross-tenant leak pattern this project has hit and fixed before (see
    ai_examguard_multi_tenancy memory) - this was a real regression, not hypothetical: any
    admin from any school could read/manage/delete any other school's exam sessions and
    violations (including viewing their students' evidence photos) via the four functions
    below, purely because they never called this."""
    return (
        db.query(Course.school_id)
        .join(Subject, Subject.course_id == Course.id)
        .join(Exam, Exam.subject_id == Subject.id)
        .filter(Exam.id == session.exam_id)
        .scalar()
    )


def require_session_read_access(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExamSession:
    session = db.query(ExamSession).filter(ExamSession.id == session_id).first()

    if session is None:
        raise HTTPException(status_code=404, detail="Exam session not found.")

    role = current_user.role.name.lower()

    if role == "admin":
        if _session_school_id(session, db) != current_user.school_id:
            raise HTTPException(status_code=404, detail="Exam session not found.")
        return session

    if role == "instructor" and _owning_instructor_matches(session, current_user, db):
        return session

    if role == "student":
        student = db.query(Student).filter(Student.user_id == current_user.id).first()
        if student is not None and session.student_id == student.id:
            return session

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You do not have permission to access this exam session."
    )


def require_session_manage_access(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExamSession:
    session = db.query(ExamSession).filter(ExamSession.id == session_id).first()

    if session is None:
        raise HTTPException(status_code=404, detail="Exam session not found.")

    role = current_user.role.name.lower()

    if role == "admin":
        if _session_school_id(session, db) != current_user.school_id:
            raise HTTPException(status_code=404, detail="Exam session not found.")
        return session

    if role == "instructor" and _owning_instructor_matches(session, current_user, db):
        return session

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You do not have permission to manage this exam session."
    )


def _get_violation_and_session(violation_id: int, db: Session) -> tuple[Violation, ExamSession]:
    violation = db.query(Violation).filter(Violation.id == violation_id).first()
    if violation is None:
        raise HTTPException(status_code=404, detail="Violation not found.")

    session = db.query(ExamSession).filter(ExamSession.id == violation.exam_session_id).first()
    if session is None:
        raise HTTPException(status_code=404, detail="Exam session not found.")

    return violation, session


def require_violation_owner_student(
    violation_id: int,
    db: Session = Depends(get_db),
    student: Student = Depends(get_current_student),
) -> Violation:
    violation, session = _get_violation_and_session(violation_id, db)

    if session.student_id != student.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This violation does not belong to you."
        )

    return violation


def require_violation_read_access(
    violation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Violation:
    violation, session = _get_violation_and_session(violation_id, db)

    role = current_user.role.name.lower()

    if role == "admin":
        if _session_school_id(session, db) != current_user.school_id:
            raise HTTPException(status_code=404, detail="Violation not found.")
        return violation

    if role == "instructor" and _owning_instructor_matches(session, current_user, db):
        return violation

    if role == "student":
        student = db.query(Student).filter(Student.user_id == current_user.id).first()
        if student is not None and session.student_id == student.id:
            return violation

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You do not have permission to access this violation."
    )


def require_violation_manage_access(
    violation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Violation:
    violation, session = _get_violation_and_session(violation_id, db)

    role = current_user.role.name.lower()

    if role == "admin":
        if _session_school_id(session, db) != current_user.school_id:
            raise HTTPException(status_code=404, detail="Violation not found.")
        return violation

    if role == "instructor" and _owning_instructor_matches(session, current_user, db):
        return violation

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You do not have permission to manage this violation."
    )
