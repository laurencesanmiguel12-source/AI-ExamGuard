from pydantic import BaseModel, ConfigDict

from app.schemas.subject import SubjectResponse


class InstructorSubjectCreate(BaseModel):
    subject_id: int


class InstructorSubjectResponse(BaseModel):
    id: int
    instructor_id: int
    subject_id: int

    model_config = ConfigDict(
        from_attributes=True
    )


class InstructorSubjectWithSubjectResponse(InstructorSubjectResponse):
    subject: SubjectResponse
