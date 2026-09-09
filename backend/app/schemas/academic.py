from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


# --- academic year --------------------------------------------------------------------------

class AcademicYearCreate(BaseModel):
    # Free text: institutions write this differently ("2026-2027", "AY 2026-27", "SY 2026-2027")
    # and it is a label, not something to compute on.
    label: str = Field(min_length=1, max_length=50)
    starts_on: date
    ends_on: date
    make_current: bool = False


class AcademicYearResponse(BaseModel):
    id: int
    label: str
    starts_on: date
    ends_on: date
    is_current: bool

    model_config = ConfigDict(from_attributes=True)


# --- term -----------------------------------------------------------------------------------

class TermCreate(BaseModel):
    academic_year_id: int
    name: str = Field(min_length=1, max_length=50)
    # Ordering within the year, explicit rather than inferred from dates - a summer term may
    # overlap or abut the semesters around it depending on the institution.
    sequence: int = Field(ge=1, le=12)
    starts_on: date
    ends_on: date


class TermStatusRequest(BaseModel):
    status: str


class TermResponse(BaseModel):
    id: int
    academic_year_id: int
    name: str
    sequence: int
    starts_on: date
    ends_on: date
    status: str

    model_config = ConfigDict(from_attributes=True)


# --- section --------------------------------------------------------------------------------

class SectionCreate(BaseModel):
    subject_id: int
    term_id: int
    instructor_id: int
    code: str = Field(min_length=1, max_length=20)
    capacity: int | None = Field(default=None, ge=1)
    schedule: str | None = Field(default=None, max_length=200)


class SectionResponse(BaseModel):
    id: int
    subject_id: int
    term_id: int
    instructor_id: int
    code: str
    capacity: int | None = None
    schedule: str | None = None

    # Denormalised for display. Without these the client has to re-join four tables just to render
    # one row, which is exactly the pattern that left the instructor list showing a bare user id.
    label: str | None = None
    subject_code: str | None = None
    subject_name: str | None = None
    course_code: str | None = None
    term_name: str | None = None
    academic_year_label: str | None = None
    instructor_name: str | None = None
    enrolled_count: int = 0

    model_config = ConfigDict(from_attributes=True)


# --- enrolment ------------------------------------------------------------------------------

class EnrollRequest(BaseModel):
    student_ids: list[int]


class EnrollmentStatusRequest(BaseModel):
    status: str


class EnrollResponse(BaseModel):
    enrolled: int
    reinstated: int
    skipped_already_enrolled: int
    errors: list[str] = []


class EnrollmentResponse(BaseModel):
    id: int
    section_id: int
    student_id: int
    status: str
    enrolled_at: datetime
    student_name: str | None = None
    student_number: str | None = None

    model_config = ConfigDict(from_attributes=True)
