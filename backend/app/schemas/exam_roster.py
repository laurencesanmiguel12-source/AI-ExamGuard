from pydantic import BaseModel, ConfigDict

from app.schemas.student import StudentResponse


class ExamRosterBase(BaseModel):
    student_id: int


class ExamRosterCreate(ExamRosterBase):
    pass


class ExamRosterResponse(ExamRosterBase):
    id: int
    exam_id: int

    model_config = ConfigDict(
        from_attributes=True
    )


class ExamRosterWithStudentResponse(ExamRosterResponse):
    student: StudentResponse
