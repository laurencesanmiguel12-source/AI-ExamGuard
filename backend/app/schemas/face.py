from pydantic import BaseModel


class FaceEnrollResponse(BaseModel):
    enrolled: bool
    samples_used: int


class FaceCheckResponse(BaseModel):
    face_detected: bool | None
    identity_match: bool | None
    confidence: float | None
    # True when face_detected is False but the pose-model fallback still sees a person - i.e. a
    # head-down tilt lost facial landmarks rather than the student actually leaving frame. Lets
    # the frontend show "HEAD DOWN" instead of "NO FACE" for this case. Always False otherwise.
    person_present: bool = False
