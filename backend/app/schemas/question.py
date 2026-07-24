from pydantic import BaseModel, ConfigDict

from app.schemas.choice import ChoiceResponse


class QuestionBase(BaseModel):
    question_text: str
    question_type: str
    points: int
    order_number: int


class QuestionCreate(QuestionBase):
    pass


class QuestionUpdate(BaseModel):
    question_text: str | None = None
    question_type: str | None = None
    points: int | None = None
    order_number: int | None = None


class QuestionResponse(QuestionBase):
    id: int
    exam_id: int

    model_config = ConfigDict(
        from_attributes=True
    )


class QuestionWithChoicesResponse(QuestionResponse):
    choices: list[ChoiceResponse] = []
