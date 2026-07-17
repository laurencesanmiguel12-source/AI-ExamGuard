from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.exam import Exam
from app.models.subject import Subject
from app.models.instructor import Instructor
from app.schemas.exam import ExamCreate, ExamUpdate


class ExamService:

    @staticmethod
    def get_all(db: Session):
        return db.query(Exam).all()

    @staticmethod
    def get_by_id(exam_id: int, db: Session):

        exam = (
            db.query(Exam)
            .filter(Exam.id == exam_id)
            .first()
        )

        if exam is None:
            raise HTTPException(
                status_code=404,
                detail="Exam not found."
            )

        return exam

    @staticmethod
    def create(request: ExamCreate, db: Session):

        subject = (
            db.query(Subject)
            .filter(Subject.id == request.subject_id)
            .first()
        )

        if subject is None:
            raise HTTPException(
                status_code=404,
                detail="Subject not found."
            )

        instructor = (
            db.query(Instructor)
            .filter(Instructor.id == request.instructor_id)
            .first()
        )

        if instructor is None:
            raise HTTPException(
                status_code=404,
                detail="Instructor not found."
            )

        exam = Exam(**request.model_dump())

        db.add(exam)
        db.commit()
        db.refresh(exam)

        return exam

    @staticmethod
    def update(exam_id: int, request: ExamUpdate, db: Session):

        exam = ExamService.get_by_id(exam_id, db)

        update_data = request.model_dump(exclude_unset=True)

        for key, value in update_data.items():
            setattr(exam, key, value)

        db.commit()
        db.refresh(exam)

        return exam

    @staticmethod
    def delete(exam_id: int, db: Session):

        exam = ExamService.get_by_id(exam_id, db)

        db.delete(exam)
        db.commit()

        return {
            "message": "Exam deleted successfully."
        }