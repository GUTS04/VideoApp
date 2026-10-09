import uuid

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.user_block import UserBlock


class BlockService:
    @staticmethod
    def is_blocked(db: Session, user_a: uuid.UUID, user_b: uuid.UUID) -> bool:
        if user_a == user_b:
            return False
        record = db.scalar(
            select(UserBlock).where(
                or_(
                    (UserBlock.blocker_id == user_a) & (UserBlock.blocked_id == user_b),
                    (UserBlock.blocker_id == user_b) & (UserBlock.blocked_id == user_a),
                )
            )
        )
        return record is not None

    @staticmethod
    def block_user(db: Session, *, blocker_id: uuid.UUID, blocked_id: uuid.UUID) -> UserBlock:
        if blocker_id == blocked_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot block yourself")
        blocked = db.get(User, blocked_id)
        if not blocked:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        existing = db.scalar(
            select(UserBlock).where(
                UserBlock.blocker_id == blocker_id,
                UserBlock.blocked_id == blocked_id,
            )
        )
        if existing:
            return existing
        record = UserBlock(blocker_id=blocker_id, blocked_id=blocked_id)
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def unblock_user(db: Session, *, blocker_id: uuid.UUID, blocked_id: uuid.UUID) -> None:
        record = db.scalar(
            select(UserBlock).where(
                UserBlock.blocker_id == blocker_id,
                UserBlock.blocked_id == blocked_id,
            )
        )
        if record:
            db.delete(record)
            db.commit()

    @staticmethod
    def list_blocked(db: Session, blocker_id: uuid.UUID) -> list[UserBlock]:
        return list(
            db.scalars(select(UserBlock).where(UserBlock.blocker_id == blocker_id).order_by(UserBlock.created_at.desc()))
        )
