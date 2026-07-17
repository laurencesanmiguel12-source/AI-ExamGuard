from pydantic import BaseModel, EmailStr
from pydantic.config import ConfigDict


class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    first_name: str
    last_name: str
    role_id: int
    is_active: bool

    model_config = ConfigDict(
        from_attributes=True
    )