from pydantic import BaseModel, EmailStr, model_validator
from pydantic.config import ConfigDict


class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    first_name: str
    last_name: str
    role_id: int
    role_name: str
    school_id: int
    is_active: bool

    model_config = ConfigDict(
        from_attributes=True
    )

    @model_validator(mode="before")
    @classmethod
    def _inject_role_name(cls, obj):
        if hasattr(obj, "role") and obj.role is not None:
            obj.role_name = obj.role.name.lower()
        return obj