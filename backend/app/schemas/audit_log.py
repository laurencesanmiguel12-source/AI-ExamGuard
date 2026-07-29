from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    id: int
    actor_user_id: int
    actor_email: str
    action: str
    resource_type: str
    resource_id: int
    detail: str | None = None
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )
