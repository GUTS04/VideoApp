import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


ReportReason = Literal[
    "harassment",
    "inappropriate_content",
    "spam",
    "underage",
    "other",
]


class CreateReportRequest(BaseModel):
    reported_user_id: uuid.UUID
    reason: ReportReason
    description: str | None = Field(default=None, max_length=2000)
    call_session_id: uuid.UUID | None = None


class ReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    reporter_id: uuid.UUID
    reported_id: uuid.UUID
    reason: str
    description: str | None
    call_session_id: uuid.UUID | None
    created_at: datetime
