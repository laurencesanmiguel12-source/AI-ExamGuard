from pydantic import BaseModel, ConfigDict


class ChoiceBase(BaseModel):
    choice_text: str
    is_correct: bool = False


class ChoiceCreate(ChoiceBase):
    pass


class ChoiceUpdate(BaseModel):
    choice_text: str | None = None
    is_correct: bool | None = None


class ChoiceResponse(ChoiceBase):
    id: int
    question_id: int

    model_config = ConfigDict(
        from_attributes=True
    )


class ChoicePublicResponse(BaseModel):
    """Same as ChoiceResponse but deliberately omits is_correct - used wherever a student can see
    a question's choices before/while taking the exam, so the answer key is never exposed in the
    response body regardless of what the frontend chooses to render."""
    id: int
    question_id: int
    choice_text: str

    model_config = ConfigDict(
        from_attributes=True
    )
