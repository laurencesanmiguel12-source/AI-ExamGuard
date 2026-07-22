from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ExamBase(BaseModel):
    title: str
    description: str | None = None
    duration_minutes: int
    total_points: int = 0
    passing_score: int
    start_time: datetime
    end_time: datetime
    is_active: bool = False
    subject_id: int
    instructor_id: int


class ExamCreate(ExamBase):
    pass


class ExamUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    duration_minutes: int | None = None
    total_points: int | None = None
    passing_score: int | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    is_active: bool | None = None
    subject_id: int | None = None
    instructor_id: int | None = None


class ExamResponse(ExamBase):
    id: int

    model_config = ConfigDict(
        from_attributes=True
    )