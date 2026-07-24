from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ExamSessionCreate(BaseModel):
    exam_id: int


class ExamSessionUpdate(BaseModel):
    score: int | None = None
    status: str | None = None
    submitted_at: datetime | None = None


class ExamSessionResponse(BaseModel):
    id: int
    student_id: int
    exam_id: int
    started_at: datetime
    submitted_at: datetime | None
    score: int
    status: str
    percentage: float
    passed: bool

    model_config = ConfigDict(
        from_attributes=True
    )
