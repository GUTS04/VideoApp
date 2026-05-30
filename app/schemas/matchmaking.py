from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.ws_messages import utc_now_iso


# --- Client → server ---


class IncomingJoinQueue(BaseModel):
    type: Literal["join_queue"] = "join_queue"


class IncomingLeaveQueue(BaseModel):
    type: Literal["leave_queue"] = "leave_queue"


class IncomingNextPartner(BaseModel):
    type: Literal["next_partner"] = "next_partner"


# --- Server → client ---


class PartnerInfo(BaseModel):
    user_id: str
    username: str
    gender: str | None = None


class QueueJoinedEvent(BaseModel):
    type: Literal["queue_joined"] = "queue_joined"
    queue_size: int
    position: int


class QueueLeftEvent(BaseModel):
    type: Literal["queue_left"] = "queue_left"


class MatchFoundEvent(BaseModel):
    type: Literal["match_found"] = "match_found"
    match_id: str
    partner: PartnerInfo
    matched_at: str = Field(default_factory=utc_now_iso)


class PartnerDisconnectedEvent(BaseModel):
    type: Literal["partner_disconnected"] = "partner_disconnected"
    match_id: str
    partner: PartnerInfo
    reason: Literal["disconnect", "left_queue", "next_partner", "match_ended"]
    message: str
