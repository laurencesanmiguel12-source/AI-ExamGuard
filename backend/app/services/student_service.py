import os

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import is_super_admin
from app.auth.service import AuthService
from app.models.course import Course
from app.models.student import Student
from app.models.user import User
from app.schemas.student import StudentCreate, StudentUpdate


class StudentService:

    @staticmethod
    def get_all(current_user: User, db: Session):
        query = db.query(Student).join(User, Student.user_id == User.id)
        if not is_super_admin(current_user):
            query = query.filter(User.school_id == current_user.school_id)
        return query.all()

    @staticmethod
    def get_by_id(student_id: int, current_user: User, db: Session):

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

        if not is_super_admin(current_user) and student.user.school_id != current_user.school_id:
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to manage this student."
            )

        return student

    @staticmethod
    def create(request: StudentCreate, admin: User, db: Session):

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

        if course.school_id != admin.school_id:
            raise HTTPException(
                status_code=403,
                detail="This course belongs to a different school."
            )

        # school_id is always the calling admin's own school, never client-supplied - same
        # never-trust-the-client derivation as Exam.instructor_id.
        user = AuthService.create_user_account(
            request.email, request.password,
            request.first_name, request.last_name, "student", admin.school_id, db,
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
    def update(student_id: int, request: StudentUpdate, current_user: User, db: Session):

        student = StudentService.get_by_id(student_id, current_user, db)

        if request.student_number is not None:
            student.student_number = request.student_number

        if request.course_id is not None:
            course = db.query(Course).filter(Course.id == request.course_id).first()
            if course is None:
                raise HTTPException(status_code=404, detail="Course not found.")
            if not is_super_admin(current_user) and course.school_id != current_user.school_id:
                raise HTTPException(status_code=403, detail="This course belongs to a different school.")
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
    def delete(student_id: int, current_user: User, db: Session):

        student = StudentService.get_by_id(student_id, current_user, db)

        # The enrolled face model is a real biometric artifact on disk, not just a DB row - delete
        # it here too, otherwise it's silently orphaned forever with no record pointing back to it.
        if student.face_model_path and os.path.exists(student.face_model_path):
            os.remove(student.face_model_path)

        db.delete(student)
        db.commit()

        return {
            "message": "Student deleted successfully."
        }