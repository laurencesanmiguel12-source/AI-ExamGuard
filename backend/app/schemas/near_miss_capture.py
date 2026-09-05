from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NearMissCandidate(BaseModel):
    """A frame awaiting review. `confidence` is the point of the record - it tells the reviewer
    how close the detector came to firing, and lets the queue put the most informative frames
    first."""
    id: int
    exam_session_id: int
    detector: str
    confidence: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NearMissResponse(NearMissCandidate):
    training_review_status: str
    training_exported_at: datetime | None = None


class NearMissReviewRequest(BaseModel):
    decision: str  # "APPROVED" or "REJECTED"
