from pydantic import BaseModel, ConfigDict


class QuestionBase(BaseModel):
    question_text: str
    question_type: str
    points: int
    order_number: int
    exam_id: int


class QuestionCreate(QuestionBase):
    pass


class QuestionUpdate(BaseModel):
    question_text: str | None = None
    question_type: str | None = None
    points: int | None = None
    order_number: int | None = None
    exam_id: int | None = None


class QuestionResponse(QuestionBase):
    id: int

    model_config = ConfigDict(
        from_attributes=True
    )