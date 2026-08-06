import os

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.auth.service import AuthService
from app.models.course import Course
from app.models.student import Student
from app.models.user import User
from app.schemas.student import StudentCreate, StudentUpdate


class StudentService:

    @staticmethod
    def get_all(db: Session):
        return db.query(Student).all()

    @staticmethod
    def get_by_id(student_id: int, db: Session):

        student = (
            db.query(Student)
            .filter(Student.id == student_id)
            .first()
        )

        if student is None:
            raise HTTPException(
                status_code=404,
                detail="Student not found."
            )

        return student

    @staticmethod
    def create(request: StudentCreate, db: Session):

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

        user = AuthService.create_user_account(
            request.username, request.email, request.password,
            request.first_name, request.last_name, "student", db,
        )

        # Same generation scheme as public self-registration (AuthService.register) - user IDs
        # are already unique/sequential, so this can't collide without a counter table.
        student = Student(
            student_number=f"STU{user.id:05d}",
            user_id=user.id,
            course_id=request.course_id
        )

        db.add(student)
        db.commit()
        db.refresh(student)

        return student

    @staticmethod
    def update(student_id: int, request: StudentUpdate, db: Session):

        student = StudentService.get_by_id(student_id, db)

        if request.student_number is not None:
            student.student_number = request.student_number

        if request.course_id is not None:
            student.course_id = request.course_id

        if request.accommodation_notes is not None:
            student.accommodation_notes = request.accommodation_notes

        if request.skip_face_check is not None:
            student.skip_face_check = request.skip_face_check

        if request.skip_object_check is not None:
            student.skip_object_check = request.skip_object_check

        if request.extra_time_minutes is not None:
            student.extra_time_minutes = request.extra_time_minutes

        db.commit()
        db.refresh(student)

        return student

    @staticmethod
    def delete(student_id: int, db: Session):

        student = StudentService.get_by_id(student_id, db)

        # The enrolled face model is a real biometric artifact on disk, not just a DB row - delete
        # it here too, otherwise it's silently orphaned forever with no record pointing back to it.
        if student.face_model_path and os.path.exists(student.face_model_path):
            os.remove(student.face_model_path)

        db.delete(student)
        db.commit()

        return {
            "message": "Student deleted successfully."
        }