from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from app.schemas.email_typo import check_email_typo


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

    @field_validator("email")
    @classmethod
    def _reject_mistyped_provider(cls, value: str) -> str:
        check_email_typo(value)
        return value

class InstructorUpdate(BaseModel):
    """Everything an admin can correct about an instructor without deleting the account.

    Name and email live on the linked User row, which is why they were missing here for so long -
    the edit form could only reach the Instructor row and so could only change a payroll number.
    Correcting a misspelled name is the single most likely reason to open this form.
    """

    employee_number: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    # No typo validator here, deliberately - see AuthService.update_user_identity. A field
    # validator cannot see the address the record already has, so guarding here would make the one
    # account that already HAS a mistyped address the one account nobody can edit.
    email: EmailStr | None = None


class InstructorAssignment(BaseModel):
    subject_id: int
    subject_code: str
    subject_name: str
    course_id: int | None = None
    course_code: str | None = None
    course_name: str | None = None


class InstructorResponse(InstructorBase):
    id: int
    # The list used to render employee_number and a raw user_id, because those were the only
    # fields this response carried - reported by the defense panel as "Instructor should have
    # complete information especially the Name". Sourced from model properties, the same way
    # StudentResponse.student_name already was.
    instructor_name: str | None = None
    email: str | None = None
    # The stored halves, so the edit form can fill itself in without splitting the display name.
    first_name: str | None = None
    last_name: str | None = None
    # Subject AND course, so two instructors on the same subject can be told apart.
    assignments: list[InstructorAssignment] = []

    model_config = ConfigDict(
        from_attributes=True
    )