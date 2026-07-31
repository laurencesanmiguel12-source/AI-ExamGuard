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
    has_evidence: bool = False
    question_id: int | None = None
    question_text: str | None = None
    question_type: str | None = None
    appeal_reason: str | None = None
    appeal_status: str | None = None
    appeal_response: str | None = None
    appeal_reviewed_at: datetime | None = None

    model_config = ConfigDict(
        from_attributes=True
    )


class ViolationAppealRequest(BaseModel):
    reason: str


class ViolationAppealReviewRequest(BaseModel):
    status: str  # "UPHELD" or "OVERTURNED"
    response: str


class LiveSessionResponse(BaseModel):
    session_id: int
    student_id: int
    student_number: str
    student_name: str
    exam_id: int
    exam_title: str
    started_at: datetime
    risk_score: float
    violation_counts: dict[str, int]


class RecentViolation(BaseModel):
    session_id: int
    student_number: str
    student_name: str
    exam_id: int
    event_type: str
    detail: str | None = None
    created_at: datetime


class LiveMonitorResponse(BaseModel):
    sessions: list[LiveSessionResponse]
    recent_events: list[RecentViolation]


class RiskTimelinePoint(BaseModel):
    time: datetime
    risk: float


class RiskSummaryResponse(BaseModel):
    risk_score: float
    timeline: list[RiskTimelinePoint]
