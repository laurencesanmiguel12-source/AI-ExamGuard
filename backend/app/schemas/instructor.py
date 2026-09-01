from pydantic import BaseModel, ConfigDict, EmailStr


class InstructorBase(BaseModel):
    employee_number: str
    user_id: int


class InstructorCreate(BaseModel):
    employee_number: str
    email: EmailStr
    password: str
    first_name: str
    last_name: str


class InstructorUpdate(BaseModel):
    employee_number: str | None = None


class InstructorResponse(InstructorBase):
    id: int

    model_config = ConfigDict(
        from_attributes=True
    )