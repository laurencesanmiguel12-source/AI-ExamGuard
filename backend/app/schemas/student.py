from pydantic import BaseModel, ConfigDict


class StudentBase(BaseModel):
    student_number: str
    user_id: int
    course_id: int


class StudentCreate(StudentBase):
    pass


class StudentUpdate(BaseModel):
    student_number: str | None = None
    user_id: int | None = None
    course_id: int | None = None


class StudentResponse(StudentBase):
    id: int

    model_config = ConfigDict(
        from_attributes=True
    )