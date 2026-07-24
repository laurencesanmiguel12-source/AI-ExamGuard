from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.exam import Exam
from app.models.question import Question
from app.schemas.question import QuestionCreate, QuestionUpdate


class QuestionService:

    @staticmethod
    def create(exam: Exam, request: QuestionCreate, db: Session):

        question = Question(exam_id=exam.id, **request.model_dump())

        db.add(question)
        db.commit()
        db.refresh(question)

        return question

    @staticmethod
    def get_all_for_exam(exam: Exam, db: Session):

        return (
            db.query(Question)
            .filter(Question.exam_id == exam.id)
            .order_by(Question.order_number)
            .all()
        )

    @staticmethod
    def get_owned(exam: Exam, question_id: int, db: Session):

        question = (
            db.query(Question)
            .filter(Question.id == question_id, Question.exam_id == exam.id)
            .first()
        )

        if question is None:
            raise HTTPException(
                status_code=404,
                detail="Question not found for this exam."
            )

        return question

    @staticmethod
    def update(exam: Exam, question_id: int, request: QuestionUpdate, db: Session):

        question = QuestionService.get_owned(exam, question_id, db)

        update_data = request.model_dump(exclude_unset=True)

        for key, value in update_data.items():
            setattr(question, key, value)

        db.commit()
        db.refresh(question)

        return question

    @staticmethod
    def delete(exam: Exam, question_id: int, db: Session):

        question = QuestionService.get_owned(exam, question_id, db)

        db.delete(question)
        db.commit()

        return {
            "message": "Question deleted successfully."
        }
