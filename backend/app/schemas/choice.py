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
