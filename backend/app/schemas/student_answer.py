from pydantic import BaseModel, ConfigDict


class StudentAnswerCreate(BaseModel):
    question_id: int
    choice_id: int


class StudentAnswerUpdate(BaseModel):
    choice_id: int | None = None
    answer_text: str | None = None


class StudentAnswerResponse(BaseModel):
    id: int
    exam_session_id: int
    question_id: int
    choice_id: int | None
    answer_text: str | None
    is_correct: bool
    points_awarded: int

    model_config = ConfigDict(
        from_attributes=True
    )