import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BlockUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    blocker_id: uuid.UUID
    blocked_id: uuid.UUID
    created_at: datetime


class BlockListResponse(BaseModel):
    items: list[BlockUserResponse]
