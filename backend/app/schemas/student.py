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
    accommodation_notes: str | None = None
    skip_face_check: bool | None = None
    skip_object_check: bool | None = None
    extra_time_minutes: int | None = None


class StudentResponse(StudentBase):
    id: int
    student_name: str | None = None
    face_model_path: str | None = None
    accommodation_notes: str | None = None
    skip_face_check: bool = False
    skip_object_check: bool = False
    extra_time_minutes: int = 0

    model_config = ConfigDict(
        from_attributes=True
    )