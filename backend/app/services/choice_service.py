from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.choice import Choice
from app.models.question import Question
from app.schemas.choice import ChoiceCreate, ChoiceUpdate


class ChoiceService:

    @staticmethod
    def create(request: ChoiceCreate, db: Session):

        question = (
            db.query(Question)
            .filter(Question.id == request.question_id)
            .first()
        )

        if question is None:
            raise HTTPException(
                status_code=404,
                detail="Question not found."
            )

        choice = Choice(**request.model_dump())

        db.add(choice)
        db.commit()
        db.refresh(choice)

        return choice

    @staticmethod
    def get_all(db: Session):

        return db.query(Choice).all()

    @staticmethod
    def get_by_id(choice_id: int, db: Session):

        choice = (
            db.query(Choice)
            .filter(Choice.id == choice_id)
            .first()
        )

        if choice is None:
            raise HTTPException(
                status_code=404,
                detail="Choice not found."
            )

        return choice

    @staticmethod
    def update(choice_id: int, request: ChoiceUpdate, db: Session):

        choice = (
            db.query(Choice)
            .filter(Choice.id == choice_id)
            .first()
        )

        if choice is None:
            raise HTTPException(
                status_code=404,
                detail="Choice not found."
            )

        update_data = request.model_dump(exclude_unset=True)

        for key, value in update_data.items():
            setattr(choice, key, value)

        db.commit()
        db.refresh(choice)

        return choice

    @staticmethod
    def delete(choice_id: int, db: Session):

        choice = (
            db.query(Choice)
            .filter(Choice.id == choice_id)
            .first()
        )

        if choice is None:
            raise HTTPException(
                status_code=404,
                detail="Choice not found."
            )

        db.delete(choice)
        db.commit()

        return {
            "message": "Choice deleted successfully."
        }