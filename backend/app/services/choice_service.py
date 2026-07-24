from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.choice import Choice
from app.models.question import Question
from app.schemas.choice import ChoiceCreate, ChoiceUpdate


class ChoiceService:

    @staticmethod
    def create(question: Question, request: ChoiceCreate, db: Session):

        choice = Choice(question_id=question.id, **request.model_dump())

        db.add(choice)
        db.commit()
        db.refresh(choice)

        return choice

    @staticmethod
    def get_owned(question: Question, choice_id: int, db: Session):

        choice = (
            db.query(Choice)
            .filter(Choice.id == choice_id, Choice.question_id == question.id)
            .first()
        )

        if choice is None:
            raise HTTPException(
                status_code=404,
                detail="Choice not found for this question."
            )

        return choice

    @staticmethod
    def update(question: Question, choice_id: int, request: ChoiceUpdate, db: Session):

        choice = ChoiceService.get_owned(question, choice_id, db)

        update_data = request.model_dump(exclude_unset=True)

        for key, value in update_data.items():
            setattr(choice, key, value)

        db.commit()
        db.refresh(choice)

        return choice

    @staticmethod
    def delete(question: Question, choice_id: int, db: Session):

        choice = ChoiceService.get_owned(question, choice_id, db)

        db.delete(choice)
        db.commit()

        return {
            "message": "Choice deleted successfully."
        }
