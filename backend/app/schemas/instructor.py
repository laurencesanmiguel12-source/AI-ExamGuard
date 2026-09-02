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
    # An instructor with no subject cannot create an exam at all (ExamService's
    # _require_subject_assignment 403s), and with no exam of their own every roster is closed to
    # them by require_exam_owner - so an account created without one is a dead end until an admin
    # remembers to assign a subject separately. Optional to keep the old request shape working.
    subject_ids: list[int] = []


class InstructorUpdate(BaseModel):
    employee_number: str | None = None


class InstructorResponse(InstructorBase):
    id: int

    model_config = ConfigDict(
        from_attributes=True
    )