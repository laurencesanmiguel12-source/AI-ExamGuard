from pydantic import BaseModel, ConfigDict


class InstructorBase(BaseModel):
    employee_number: str
    user_id: int


class InstructorCreate(InstructorBase):
    pass


class InstructorUpdate(BaseModel):
    employee_number: str | None = None


class InstructorResponse(InstructorBase):
    id: int

    model_config = ConfigDict(
        from_attributes=True
    )