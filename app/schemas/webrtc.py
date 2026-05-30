from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.ws_messages import utc_now_iso


class SessionDescriptionPayload(BaseModel):
    """WebRTC RTCSessionDescriptionInit-compatible payload."""

    type: Literal["offer", "answer"]
    sdp: str = Field(..., min_length=1)


class IceCandidatePayload(BaseModel):
    """WebRTC RTCIceCandidateInit-compatible payload."""

    candidate: str = Field(..., min_length=1)
    sdp_mid: str | None = Field(default=None, alias="sdpMid")
    sdp_m_line_index: int | None = Field(default=None, alias="sdpMLineIndex")
    username_fragment: str | None = Field(default=None, alias="usernameFragment")

    model_config = ConfigDict(populate_by_name=True)


# --- Client → server (matched sessions only) ---


class IncomingWebRtcOffer(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "type": "webrtc_offer",
                    "match_id": "match-uuid",
                    "sdp": {"type": "offer", "sdp": "v=0..."},
                }
            ]
        }
    )

    type: Literal["webrtc_offer"] = "webrtc_offer"
    match_id: str | None = Field(default=None, description="Must match active session if provided")
    sdp: SessionDescriptionPayload


class IncomingWebRtcAnswer(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "type": "webrtc_answer",
                    "match_id": "match-uuid",
                    "sdp": {"type": "answer", "sdp": "v=0..."},
                }
            ]
        }
    )

    type: Literal["webrtc_answer"] = "webrtc_answer"
    match_id: str | None = None
    sdp: SessionDescriptionPayload


class IncomingIceCandidate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "type": "ice_candidate",
                    "match_id": "match-uuid",
                    "candidate": {
                        "candidate": "candidate:1 1 UDP 2130706431 192.168.0.1 54321 typ host",
                        "sdpMid": "0",
                        "sdpMLineIndex": 0,
                    },
                }
            ]
        }
    )

    type: Literal["ice_candidate"] = "ice_candidate"
    match_id: str | None = None
    candidate: IceCandidatePayload


# --- Server → client (forwarded from partner) ---


class WebRtcOfferEvent(BaseModel):
    type: Literal["webrtc_offer"] = "webrtc_offer"
    match_id: str
    from_user_id: str
    from_username: str
    sdp: SessionDescriptionPayload
    sent_at: str = Field(default_factory=utc_now_iso)


class WebRtcAnswerEvent(BaseModel):
    type: Literal["webrtc_answer"] = "webrtc_answer"
    match_id: str
    from_user_id: str
    from_username: str
    sdp: SessionDescriptionPayload
    sent_at: str = Field(default_factory=utc_now_iso)


class IceCandidateEvent(BaseModel):
    type: Literal["ice_candidate"] = "ice_candidate"
    match_id: str
    from_user_id: str
    from_username: str
    candidate: IceCandidatePayload
    sent_at: str = Field(default_factory=utc_now_iso)
