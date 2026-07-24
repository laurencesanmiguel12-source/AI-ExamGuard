from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ViolationCreate(BaseModel):
    event_type: str
    detail: str | None = None


class ViolationResponse(BaseModel):
    id: int
    exam_session_id: int
    event_type: str
    detail: str | None = None
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )


class LiveSessionResponse(BaseModel):
    session_id: int
    student_id: int
    student_number: str
    exam_id: int
    exam_title: str
    started_at: datetime
    risk_score: float
    violation_counts: dict[str, int]


class RecentViolation(BaseModel):
    session_id: int
    student_number: str
    exam_id: int
    event_type: str
    detail: str | None = None
    created_at: datetime


class LiveMonitorResponse(BaseModel):
    sessions: list[LiveSessionResponse]
    recent_events: list[RecentViolation]
