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
    # Subject AND course, so two instructors on the same subject can be told apart.
    assignments: list[InstructorAssignment] = []

    model_config = ConfigDict(
        from_attributes=True
    )