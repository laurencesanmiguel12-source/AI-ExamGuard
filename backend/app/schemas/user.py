from pydantic import BaseModel


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role_id: int
    is_active: bool

    class Config:
        from_attributes = True