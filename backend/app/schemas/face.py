from pydantic import BaseModel


class FaceEnrollResponse(BaseModel):
    enrolled: bool
    samples_used: int


class FaceCheckResponse(BaseModel):
    face_detected: bool | None
    identity_match: bool | None
    confidence: float | None
