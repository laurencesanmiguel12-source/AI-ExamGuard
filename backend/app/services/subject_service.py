from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.course import Course
from app.models.subject import Subject
from app.models.user import User
from app.schemas.subject import SubjectCreate, SubjectUpdate


class SubjectService:

    @staticmethod
    def get_all(current_user: User, db: Session):
        return (
            db.query(Subject)
            .join(Course, Subject.course_id == Course.id)
            .filter(Course.school_id == current_user.school_id)
            .all()
        )

    @staticmethod
    def get_by_id(subject_id: int, current_user: User, db: Session):

        subject = (
            db.query(Subject)
            .filter(Subject.id == subject_id)
            .first()
        )

        if subject is None:
            raise HTTPException(
                status_code=404,
                detail="Subject not found."
            )

        if subject.course.school_id != current_user.school_id:
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to manage this subject."
            )

        return subject

    @staticmethod
    def create(request: SubjectCreate, current_user: User, db: Session):

        course = (
            db.query(Course)
            .filter(Course.id == request.course_id)
            .first()
        )

        if course is None:
            raise HTTPException(
                status_code=404,
                detail="Course not found."
            )

        if course.school_id != current_user.school_id:
            raise HTTPException(
                status_code=403,
                detail="This course belongs to a different school."
            )

        duplicate = (
            db.query(Subject)
            .filter(
                Subject.course_id == request.course_id,
                Subject.code == request.code
            )
            .first()
        )

        if duplicate:
            raise HTTPException(
                status_code=400,
                detail="Subject code already exists in this course."
            )

        subject = Subject(
            code=request.code,
            name=request.name,
            course_id=request.course_id
        )

        db.add(subject)
        db.commit()
        db.refresh(subject)

        return subject

    @staticmethod
    def update(
        subject_id: int,
        request: SubjectUpdate,
        current_user: User,
        db: Session
    ):

        subject = SubjectService.get_by_id(subject_id, current_user, db)

        if request.code is not None:
            subject.code = request.code

        if request.name is not None:
            subject.name = request.name

        if request.course_id is not None:
            course = db.query(Course).filter(Course.id == request.course_id).first()
            if course is None:
                raise HTTPException(status_code=404, detail="Course not found.")
            if course.school_id != current_user.school_id:
                raise HTTPException(status_code=403, detail="This course belongs to a different school.")
            subject.course_id = request.course_id

        db.commit()
        db.refresh(subject)

        return subject

    @staticmethod
    def delete(subject_id: int, current_user: User, db: Session):

        subject = SubjectService.get_by_id(subject_id, current_user, db)

        db.delete(subject)
        db.commit()

        return {
            "message": "Subject deleted successfully."
        }