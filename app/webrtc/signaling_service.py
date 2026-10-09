import logging
from typing import Any

from pydantic import ValidationError

from app.matchmaking.match_manager import MatchManager
from app.models.user import User
from app.schemas.webrtc import (
    IceCandidateEvent,
    IncomingIceCandidate,
    IncomingWebRtcAnswer,
    IncomingWebRtcOffer,
    WebRtcAnswerEvent,
    WebRtcOfferEvent,
)
from app.schemas.ws_messages import ErrorCode
from app.websocket.manager import ConnectionManager

logger = logging.getLogger(__name__)


class WebRtcSignalingService:
    """Forward WebRTC signaling between users in the same active match."""

    def __init__(self, match_manager: MatchManager) -> None:
        self.matches = match_manager

    async def handle_offer(
        self,
        user: User,
        data: dict[str, Any],
        ws_manager: ConnectionManager,
    ) -> dict[str, Any] | None:
        return await self._handle_signaling(
            user=user,
            data=data,
            ws_manager=ws_manager,
            schema=IncomingWebRtcOffer,
            build_event=lambda match_id, from_id, from_name, payload: WebRtcOfferEvent(
                match_id=match_id,
                from_user_id=from_id,
                from_username=from_name,
                sdp=payload.sdp,
            ),
            label="webrtc_offer",
        )

    async def handle_answer(
        self,
        user: User,
        data: dict[str, Any],
        ws_manager: ConnectionManager,
    ) -> dict[str, Any] | None:
        return await self._handle_signaling(
            user=user,
            data=data,
            ws_manager=ws_manager,
            schema=IncomingWebRtcAnswer,
            build_event=lambda match_id, from_id, from_name, payload: WebRtcAnswerEvent(
                match_id=match_id,
                from_user_id=from_id,
                from_username=from_name,
                sdp=payload.sdp,
            ),
            label="webrtc_answer",
        )

    async def handle_ice_candidate(
        self,
        user: User,
        data: dict[str, Any],
        ws_manager: ConnectionManager,
    ) -> dict[str, Any] | None:
        return await self._handle_signaling(
            user=user,
            data=data,
            ws_manager=ws_manager,
            schema=IncomingIceCandidate,
            build_event=lambda match_id, from_id, from_name, payload: IceCandidateEvent(
                match_id=match_id,
                from_user_id=from_id,
                from_username=from_name,
                candidate=payload.candidate,
            ),
            label="ice_candidate",
        )

    async def _handle_signaling(
        self,
        *,
        user: User,
        data: dict[str, Any],
        ws_manager: ConnectionManager,
        schema: type[IncomingWebRtcOffer] | type[IncomingWebRtcAnswer] | type[IncomingIceCandidate],
        build_event: Any,
        label: str,
    ) -> dict[str, Any] | None:
        logger.info("SIGNALING_RECEIVED type=%s from_user_id=%s", label, user.id)
        match = self.matches.get_match_for_user(user.id)
        if not match:
            logger.warning("SIGNALING_REJECTED_NOT_IN_MATCH type=%s from_user_id=%s", label, user.id)
            return self._error(
                ErrorCode.NOT_IN_MATCH,
                "WebRTC signaling is only allowed during an active match",
            )

        try:
            payload = schema.model_validate(data)
        except ValidationError as exc:
            return self._error(
                ErrorCode.VALIDATION_ERROR,
                f"Invalid {label} payload",
                details={
                    "fields": [
                        ".".join(str(part) for part in err.get("loc", ()))
                        for err in exc.errors()
                    ]
                },
            )

        if payload.match_id is not None and payload.match_id != match.match_id:
            return self._error(
                ErrorCode.INVALID_MESSAGE,
                "match_id does not match your active session",
                details={
                    "expected_match_id": match.match_id,
                    "received_match_id": payload.match_id,
                },
            )

        partner = match.partner_of(user.id)
        if not partner:
            return self._error(ErrorCode.MATCH_FAILED, "Active match has no partner")

        partner_id, _partner_username = partner
        if partner_id == user.id:
            return self._error(ErrorCode.SELF_MESSAGE, "Cannot send signaling to yourself")

        event = build_event(
            match.match_id,
            str(user.id),
            user.username,
            payload,
        )
        outbound = event.model_dump(by_alias=True)

        delivered = await ws_manager.send_to_user(partner_id, outbound)
        if delivered == 0:
            logger.warning(
                "SIGNALING_DELIVERY_FAILED type=%s from_user_id=%s partner_id=%s match_id=%s",
                label,
                user.id,
                partner_id,
                match.match_id,
            )
            return self._error(
                ErrorCode.USER_OFFLINE,
                "Matched partner is offline",
                details={"partner_user_id": str(partner_id), "match_id": match.match_id},
            )

        logger.info("%s %s -> %s (match=%s)", label, user.id, partner_id, match.match_id)
        return None

    @staticmethod
    def _error(
        code: ErrorCode,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "type": "error",
            "code": code,
            "message": message,
            "details": details,
        }
