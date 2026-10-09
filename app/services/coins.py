import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.coin_transaction import CoinTransaction
from app.models.user import User


class CoinService:
    @staticmethod
    def get_balance(db: Session, user_id: uuid.UUID) -> int:
        user = db.get(User, user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return user.coin_balance

    @staticmethod
    def list_transactions(
        db: Session,
        user_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[CoinTransaction], int]:
        total = db.scalar(
            select(func.count())
            .select_from(CoinTransaction)
            .where(CoinTransaction.user_id == user_id)
        ) or 0
        items = list(
            db.scalars(
                select(CoinTransaction)
                .where(CoinTransaction.user_id == user_id)
                .order_by(CoinTransaction.created_at.desc())
                .offset(skip)
                .limit(limit)
            )
        )
        return items, total

    @staticmethod
    def grant_initial_balance(db: Session, user: User) -> None:
        settings = get_settings()
        amount = settings.initial_coin_balance
        if amount <= 0:
            return
        CoinService._credit(
            db,
            user=user,
            amount=amount,
            reason="registration_bonus",
            idempotency_key=f"registration_bonus:{user.id}",
        )

    @staticmethod
    def debit(
        db: Session,
        *,
        user_id: uuid.UUID,
        amount: int,
        reason: str,
        call_session_id: uuid.UUID | None = None,
        idempotency_key: str | None = None,
    ) -> CoinTransaction:
        if amount <= 0:
            raise ValueError("Debit amount must be positive")
        user = db.scalar(select(User).where(User.id == user_id).with_for_update())
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        if idempotency_key:
            existing = db.scalar(
                select(CoinTransaction).where(CoinTransaction.idempotency_key == idempotency_key)
            )
            if existing:
                return existing
        if user.coin_balance < amount:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Insufficient coin balance",
            )
        user.coin_balance -= amount
        tx = CoinTransaction(
            user_id=user.id,
            amount=-amount,
            transaction_type="debit",
            reason=reason,
            call_session_id=call_session_id,
            idempotency_key=idempotency_key,
        )
        db.add(tx)
        db.commit()
        db.refresh(tx)
        return tx

    @staticmethod
    def _credit(
        db: Session,
        *,
        user: User,
        amount: int,
        reason: str,
        call_session_id: uuid.UUID | None = None,
        idempotency_key: str | None = None,
    ) -> CoinTransaction:
        if amount <= 0:
            raise ValueError("Credit amount must be positive")
        if idempotency_key:
            existing = db.scalar(
                select(CoinTransaction).where(CoinTransaction.idempotency_key == idempotency_key)
            )
            if existing:
                return existing
        locked = db.scalar(select(User).where(User.id == user.id).with_for_update())
        if not locked:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        locked.coin_balance += amount
        tx = CoinTransaction(
            user_id=locked.id,
            amount=amount,
            transaction_type="credit",
            reason=reason,
            call_session_id=call_session_id,
            idempotency_key=idempotency_key,
        )
        db.add(tx)
        db.commit()
        db.refresh(tx)
        return tx
