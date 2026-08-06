from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.course import Course
from app.schemas.course import CourseCreate, CourseUpdate


class CourseService:

    @staticmethod
    def get_all(db: Session, school_id: int):
        return db.query(Course).filter(Course.school_id == school_id).all()

    @staticmethod
    def get_by_id(course_id: int, db: Session):

        course = (
            db.query(Course)
            .filter(Course.id == course_id)
            .first()
        )

        if not course:
            raise HTTPException(
                status_code=404,
                detail="Course not found."
            )

        return course

    @staticmethod
    def create(request: CourseCreate, school_id: int, db: Session):

        existing = (
            db.query(Course)
            .filter(Course.code == request.code, Course.school_id == school_id)
            .first()
        )

        if existing:
            raise HTTPException(
                status_code=400,
                detail="Course already exists."
            )

        course = Course(
            code=request.code,
            name=request.name,
            school_id=school_id
        )

        db.add(course)
        db.commit()
        db.refresh(course)

        return course

    @staticmethod
    def update(
        course_id: int,
        request: CourseUpdate,
        db: Session
    ):

        course = CourseService.get_by_id(course_id, db)

        if request.code is not None:
            course.code = request.code

        if request.name is not None:
            course.name = request.name

        db.commit()
        db.refresh(course)

        return course

    @staticmethod
    def delete(course_id: int, db: Session):

        course = CourseService.get_by_id(course_id, db)

        db.delete(course)
        db.commit()

        return {
            "message": "Course deleted successfully."
        }