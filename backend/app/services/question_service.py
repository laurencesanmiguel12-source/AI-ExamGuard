from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.exam import Exam
from app.models.question import Question
from app.schemas.question import QuestionCreate, QuestionUpdate


class QuestionService:

    @staticmethod
    def create(request: QuestionCreate, db: Session):

        exam = (
            db.query(Exam)
            .filter(Exam.id == request.exam_id)
            .first()
        )

        if exam is None:
            raise HTTPException(
                status_code=404,
                detail="Exam not found."
            )

        question = Question(**request.model_dump())

        db.add(question)
        db.commit()
        db.refresh(question)

        return question

    @staticmethod
    def get_all(db: Session):

        return db.query(Question).all()

    @staticmethod
    def get_by_id(question_id: int, db: Session):

        question = (
            db.query(Question)
            .filter(Question.id == question_id)
            .first()
        )

        if question is None:
            raise HTTPException(
                status_code=404,
                detail="Question not found."
            )

        return question

    @staticmethod
    def update(question_id: int, request: QuestionUpdate, db: Session):

        question = (
            db.query(Question)
            .filter(Question.id == question_id)
            .first()
        )

        if question is None:
            raise HTTPException(
                status_code=404,
                detail="Question not found."
            )

        update_data = request.model_dump(exclude_unset=True)

        for key, value in update_data.items():
            setattr(question, key, value)

        db.commit()
        db.refresh(question)

        return question

    @staticmethod
    def delete(question_id: int, db: Session):

        question = (
            db.query(Question)
            .filter(Question.id == question_id)
            .first()
        )

        if question is None:
            raise HTTPException(
                status_code=404,
                detail="Question not found."
            )

        db.delete(question)
        db.commit()

        return {
            "message": "Question deleted successfully."
        }