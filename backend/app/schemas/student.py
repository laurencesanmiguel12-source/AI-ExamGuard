from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from app.schemas.email_typo import check_email_typo


class StudentBase(BaseModel):
    student_number: str
    user_id: int
    course_id: int


class StudentCreate(BaseModel):
    course_id: int
    email: EmailStr
    password: str
    first_name: str
    last_name: str

    @field_validator("email")
    @classmethod
    def _reject_mistyped_provider(cls, value: str) -> str:
        check_email_typo(value)
        return value

class StudentUpdate(BaseModel):
    # first_name / last_name / email live on the linked User row. Without them the edit form could
    # change a student's course and their accommodations but not the spelling of their own name.
    first_name: str | None = None
    last_name: str | None = None
    # No typo validator - same reason as InstructorUpdate.
    email: EmailStr | None = None
    student_number: str | None = None
    user_id: int | None = None
    course_id: int | None = None
    accommodation_notes: str | None = None
    skip_face_check: bool | None = None
    skip_object_check: bool | None = None
    extra_time_minutes: int | None = None



class StudentResponse(StudentBase):
    id: int
    student_name: str | None = None
    email: str | None = None
    # The stored halves, so the edit form can fill itself in without splitting the display name.
    first_name: str | None = None
    last_name: str | None = None
    face_model_path: str | None = None
    accommodation_notes: str | None = None
    skip_face_check: bool = False
    skip_object_check: bool = False
    extra_time_minutes: int = 0

    model_config = ConfigDict(
        from_attributes=True
    )