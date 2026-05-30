import logging
import uuid
from typing import Any, Literal

from app.matchmaking.match_manager import MatchManager
from app.matchmaking.queue_manager import QueueManager
from app.models.user import User
from app.schemas.gender import partner_gender_for
from app.schemas.matchmaking import (
    MatchFoundEvent,
    PartnerDisconnectedEvent,
    PartnerInfo,
    QueueJoinedEvent,
    QueueLeftEvent,
)
from app.schemas.ws_messages import ErrorCode
from app.websocket.manager import ConnectionManager

logger = logging.getLogger(__name__)

PartnerDisconnectReason = Literal["disconnect", "left_queue", "next_partner", "match_ended"]


class MatchmakingService:
    def __init__(self) -> None:
        self.queue = QueueManager()
        self.matches = MatchManager()

    async def join_queue(self, user: User, ws_manager: ConnectionManager) -> dict[str, Any] | None:
        if self.matches.is_matched(user.id):
            return self._error(
                ErrorCode.ALREADY_IN_MATCH,
                "Leave your current match before joining the queue",
            )

        if self.queue.is_queued(user.id):
            return self._error(ErrorCode.ALREADY_IN_QUEUE, "You are already in the matchmaking queue")

        partner_entry = self.queue.pop_next_compatible_partner(
            exclude_user_id=user.id,
            seeker_gender=user.gender,
        )
        if partner_entry:
            return await self._create_match_and_notify(
                user_a_id=user.id,
                user_a_username=user.username,
                user_a_gender=user.gender,
                user_b_id=partner_entry.user_id,
                user_b_username=partner_entry.username,
                user_b_gender=partner_entry.gender,
                ws_manager=ws_manager,
            )

        entry = self.queue.add(user.id, user.username, user.gender)
        position = self.queue.position(entry.user_id) or self.queue.size
        waiting_opposite = self.queue.waiting_count_for_partner_gender(user.gender)
        event = QueueJoinedEvent(queue_size=self.queue.size, position=position)
        await ws_manager.send_to_user(user.id, event.model_dump())
        logger.info(
            "User %s (%s) joined queue position=%s waiting_opposite_gender=%s",
            user.id,
            user.gender,
            position,
            waiting_opposite,
        )
        return None

    async def leave_queue(self, user: User, ws_manager: ConnectionManager) -> dict[str, Any] | None:
        if not self.queue.is_queued(user.id):
            return self._error(ErrorCode.NOT_IN_QUEUE, "You are not in the matchmaking queue")

        self.queue.remove(user.id)
        await ws_manager.send_to_user(user.id, QueueLeftEvent().model_dump())
        logger.info("User %s left queue", user.id)
        return None

    async def next_partner(
        self,
        user: User,
        ws_manager: ConnectionManager,
    ) -> dict[str, Any] | None:
        if not self.matches.is_matched(user.id):
            return self._error(ErrorCode.NOT_IN_MATCH, "You are not in an active match")

        await self._end_match_for_user(
            user.id,
            ws_manager=ws_manager,
            reason="next_partner",
            initiator_id=user.id,
        )
        return await self.join_queue(user, ws_manager)

    async def handle_user_offline(self, user_id: uuid.UUID, ws_manager: ConnectionManager) -> None:
        if self.queue.is_queued(user_id):
            self.queue.remove(user_id)
            logger.info("Removed offline user %s from queue", user_id)

        if self.matches.is_matched(user_id):
            await self._end_match_for_user(
                user_id,
                ws_manager=ws_manager,
                reason="disconnect",
                initiator_id=user_id,
            )

    async def _create_match_and_notify(
        self,
        *,
        user_a_id: uuid.UUID,
        user_a_username: str,
        user_a_gender: str,
        user_b_id: uuid.UUID,
        user_b_username: str,
        user_b_gender: str,
        ws_manager: ConnectionManager,
    ) -> dict[str, Any] | None:
        try:
            match = self.matches.create_match(
                user_a_id=user_a_id,
                user_a_username=user_a_username,
                user_a_gender=user_a_gender,
                user_b_id=user_b_id,
                user_b_username=user_b_username,
                user_b_gender=user_b_gender,
            )
        except ValueError as exc:
            logger.warning("Match creation failed: %s", exc)
            return self._error(ErrorCode.MATCH_FAILED, str(exc))

        await self._notify_match_found(
            match.match_id, user_a_id, user_b_id, user_b_username, user_b_gender, ws_manager
        )
        await self._notify_match_found(
            match.match_id, user_b_id, user_a_id, user_a_username, user_a_gender, ws_manager
        )
        logger.info(
            "Match %s: %s (%s) <-> %s (%s)",
            match.match_id,
            user_a_id,
            user_a_gender,
            user_b_id,
            user_b_gender,
        )
        return None

    async def _notify_match_found(
        self,
        match_id: str,
        user_id: uuid.UUID,
        partner_id: uuid.UUID,
        partner_username: str,
        partner_gender: str,
        ws_manager: ConnectionManager,
    ) -> None:
        event = MatchFoundEvent(
            match_id=match_id,
            partner=PartnerInfo(
                user_id=str(partner_id),
                username=partner_username,
                gender=partner_gender,
            ),
        )
        await ws_manager.send_to_user(user_id, event.model_dump())

    async def _end_match_for_user(
        self,
        user_id: uuid.UUID,
        *,
        ws_manager: ConnectionManager,
        reason: PartnerDisconnectReason,
        initiator_id: uuid.UUID,
    ) -> None:
        match = self.matches.get_match_for_user(user_id)
        if not match:
            return

        partner = match.partner_of(user_id)
        ended = self.matches.end_match(match.match_id)
        if not ended or not partner:
            return

        partner_id, _partner_username = partner
        messages = {
            "disconnect": "Your partner disconnected",
            "left_queue": "Your partner left the queue",
            "next_partner": "Your partner requested a new match",
            "match_ended": "The match has ended",
        }

        initiator_username = (
            ended.user_a_username if user_id == ended.user_a_id else ended.user_b_username
        )

        if partner_id != initiator_id:
            await self._notify_partner_disconnected(
                user_id=partner_id,
                match_id=ended.match_id,
                partner_id=user_id,
                partner_username=initiator_username,
                reason=reason,
                message=messages[reason],
                ws_manager=ws_manager,
            )

    async def _notify_partner_disconnected(
        self,
        *,
        user_id: uuid.UUID,
        match_id: str,
        partner_id: uuid.UUID,
        partner_username: str,
        reason: PartnerDisconnectReason,
        message: str,
        ws_manager: ConnectionManager,
    ) -> None:
        if not ws_manager.is_user_online(user_id):
            return
        event = PartnerDisconnectedEvent(
            match_id=match_id,
            partner=PartnerInfo(user_id=str(partner_id), username=partner_username),
            reason=reason,
            message=message,
        )
        await ws_manager.send_to_user(user_id, event.model_dump())

    @staticmethod
    def _error(code: ErrorCode, message: str, *, details: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "type": "error",
            "code": code,
            "message": message,
            "details": details,
        }

    def status_snapshot(self) -> dict[str, Any]:
        return {
            "queue_size": self.queue.size,
            "queue": self.queue.snapshot(),
            "active_matches": self.matches.active_match_count,
            "matches": self.matches.snapshot(),
            "gender_rules": {
                "male_pairs_with": partner_gender_for("male"),
                "female_pairs_with": partner_gender_for("female"),
            },
        }


matchmaking_service = MatchmakingService()
