from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class IncomingCallConnected(BaseModel):
    type: Literal["call_connected"] = "call_connected"
    match_id: str = Field(..., min_length=1)


class IncomingCallEnded(BaseModel):
    type: Literal["call_ended"] = "call_ended"
    match_id: str = Field(..., min_length=1)


class CallBillingUpdateEvent(BaseModel):
    type: Literal["call_billing_update"] = "call_billing_update"
    match_id: str
    coin_balance: int
    call_duration_seconds: int
    coins_charged: int


class CallTerminatedEvent(BaseModel):
    type: Literal["call_terminated"] = "call_terminated"
    match_id: str
    reason: Literal["insufficient_funds", "ended", "partner_left"]
    message: str
