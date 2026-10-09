import logging
import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.call_session import CallSession
from app.models.user import User
from app.services.billing import coins_for_duration_seconds
from app.services.coins import CoinService

logger = logging.getLogger(__name__)


class CallService:
    @staticmethod
    def create_pending_session(
        db: Session,
        *,
        match_id: str,
        user_a_id: uuid.UUID,
        user_b_id: uuid.UUID,
    ) -> CallSession:
        existing = db.scalar(select(CallSession).where(CallSession.match_id == match_id))
        if existing:
            return existing
        session = CallSession(
            match_id=match_id,
            user_a_id=user_a_id,
            user_b_id=user_b_id,
            status="pending",
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        return session

    @staticmethod
    def get_by_match_id(db: Session, match_id: str) -> CallSession | None:
        return db.scalar(select(CallSession).where(CallSession.match_id == match_id))

    @staticmethod
    def get_active_for_user(db: Session, user_id: uuid.UUID) -> CallSession | None:
        return db.scalar(
            select(CallSession).where(
                CallSession.status.in_(("pending", "active")),
                (CallSession.user_a_id == user_id) | (CallSession.user_b_id == user_id),
            )
        )

    @staticmethod
    def mark_user_connected(db: Session, *, match_id: str, user_id: uuid.UUID) -> CallSession:
        session = db.scalar(
            select(CallSession).where(CallSession.match_id == match_id).with_for_update()
        )
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Call session not found")
        if user_id not in (session.user_a_id, session.user_b_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a participant")

        now = datetime.now(UTC)
        if user_id == session.user_a_id:
            session.user_a_connected_at = session.user_a_connected_at or now
        else:
            session.user_b_connected_at = session.user_b_connected_at or now

        if session.user_a_connected_at and session.user_b_connected_at:
            session.status = "active"
            session.connected_at = max(session.user_a_connected_at, session.user_b_connected_at)
            session.last_billed_at = session.connected_at

        db.commit()
        db.refresh(session)
        return session

    @staticmethod
    def _billable_seconds(session: CallSession, *, until: datetime | None = None) -> int:
        if not session.connected_at:
            return 0
        end = until or session.ended_at or datetime.now(UTC)
        return max(0, int((end - session.connected_at).total_seconds()))

    @staticmethod
    def _user_charged_field(session: CallSession, user_id: uuid.UUID) -> str:
        return "user_a_coins_charged" if user_id == session.user_a_id else "user_b_coins_charged"

    @staticmethod
    def bill_incremental(db: Session, session: CallSession) -> tuple[int, int]:
        """Bill both users for elapsed time since last bill. Returns (a_delta, b_delta)."""
        if session.status != "active" or not session.connected_at or session.billing_finalized:
            return (0, 0)

        now = datetime.now(UTC)
        total_seconds = CallService._billable_seconds(session, until=now)
        total_coins = coins_for_duration_seconds(total_seconds)

        a_target = total_coins
        b_target = total_coins
        a_delta = max(0, a_target - session.user_a_coins_charged)
        b_delta = max(0, b_target - session.user_b_coins_charged)

        if a_delta == 0 and b_delta == 0:
            session.last_billed_at = now
            db.commit()
            return (0, 0)

        try:
            if a_delta:
                CoinService.debit(
                    db,
                    user_id=session.user_a_id,
                    amount=a_delta,
                    reason="call_usage",
                    call_session_id=session.id,
                    idempotency_key=f"call:{session.id}:user_a:{total_seconds}",
                )
                session.user_a_coins_charged += a_delta
            if b_delta:
                CoinService.debit(
                    db,
                    user_id=session.user_b_id,
                    amount=b_delta,
                    reason="call_usage",
                    call_session_id=session.id,
                    idempotency_key=f"call:{session.id}:user_b:{total_seconds}",
                )
                session.user_b_coins_charged += b_delta
        except HTTPException as exc:
            if exc.status_code == status.HTTP_402_PAYMENT_REQUIRED:
                broke_id = session.user_a_id if a_delta else session.user_b_id
                CallService.finalize_session(
                    db,
                    session,
                    reason="insufficient_funds",
                    terminate_user_id=broke_id,
                )
                session.status = "terminated_insufficient_funds"
                return (a_delta, b_delta)
            raise

        session.last_billed_at = now
        db.commit()
        db.refresh(session)
        return (a_delta, b_delta)

    @staticmethod
    def finalize_session(
        db: Session,
        session: CallSession,
        *,
        reason: str = "ended",
        terminate_user_id: uuid.UUID | None = None,
    ) -> CallSession:
        locked = db.scalar(
            select(CallSession).where(CallSession.id == session.id).with_for_update()
        )
        if not locked or locked.billing_finalized:
            return locked or session

        if locked.status == "active":
            CallService.bill_incremental(db, locked)

        locked.status = "terminated_insufficient_funds" if reason == "insufficient_funds" else "ended"
        locked.ended_at = locked.ended_at or datetime.now(UTC)
        locked.billing_finalized = True
        db.commit()
        db.refresh(locked)
        logger.info(
            "Call session finalized match_id=%s reason=%s terminate_user=%s",
            locked.match_id,
            reason,
            terminate_user_id,
        )
        return locked

    @staticmethod
    def end_by_match_id(db: Session, match_id: str, *, reason: str = "ended") -> CallSession | None:
        session = db.scalar(select(CallSession).where(CallSession.match_id == match_id))
        if not session:
            return None
        return CallService.finalize_session(db, session, reason=reason)
