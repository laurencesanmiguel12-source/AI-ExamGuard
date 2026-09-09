from pydantic import BaseModel, EmailStr, field_validator

from app.schemas.email_typo import check_email_typo


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    course_id: int

    @field_validator("email")
    @classmethod
    def _reject_mistyped_provider(cls, value: str) -> str:
        check_email_typo(value)
        return value

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


class TokenPayload(BaseModel):
    sub: str
    email: str
    role: str

