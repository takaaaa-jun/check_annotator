from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CurrentUserResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    user_id: int
    user_name: str
    role_id: int
    role_name: str
    login_at: datetime | None