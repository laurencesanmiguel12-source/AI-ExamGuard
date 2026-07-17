from pydantic import BaseModel, ConfigDict


class SubjectBase(BaseModel):
    code: str
    name: str
    course_id: int


class SubjectCreate(SubjectBase):
    pass


class SubjectUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    course_id: int | None = None


class SubjectResponse(SubjectBase):
    id: int

    model_config = ConfigDict(
        from_attributes=True
    )