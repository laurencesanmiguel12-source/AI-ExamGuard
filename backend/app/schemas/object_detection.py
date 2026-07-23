from pydantic import BaseModel


class ObjectCheckResponse(BaseModel):
    phone_detected: bool
    person_count: int
