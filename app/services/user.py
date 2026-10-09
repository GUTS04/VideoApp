import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.services.coins import CoinService


class UserService:
    @staticmethod
    def get_by_id(db: Session, user_id: uuid.UUID) -> User | None:
        return db.get(User, user_id)

    @staticmethod
    def get_by_email(db: Session, email: str) -> User | None:
        return db.scalar(select(User).where(User.email == email))

    @staticmethod
    def get_by_username(db: Session, username: str) -> User | None:
        return db.scalar(select(User).where(User.username == username))

    @staticmethod
    def list_users(db: Session, *, skip: int = 0, limit: int = 100) -> tuple[list[User], int]:
        total = db.scalar(select(func.count()).select_from(User)) or 0
        users = list(db.scalars(select(User).offset(skip).limit(limit).order_by(User.created_at.desc())))
        return users, total

    @staticmethod
    def create_user(db: Session, payload: UserCreate) -> User:
        if UserService.get_by_email(db, payload.email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )
        if UserService.get_by_username(db, payload.username):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already taken",
            )

        settings = get_settings()
        user = User(
            email=payload.email,
            username=payload.username,
            gender=payload.gender,
            hashed_password=hash_password(payload.password),
            coin_balance=0,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        if settings.initial_coin_balance > 0:
            CoinService.grant_initial_balance(db, user)
            db.refresh(user)
        return user

    @staticmethod
    def update_user(db: Session, user: User, payload: UserUpdate) -> User:
        data = payload.model_dump(exclude_unset=True)
        password = data.pop("password", None)

        if "email" in data and data["email"] != user.email:
            if UserService.get_by_email(db, data["email"]):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Email already registered",
                )
        if "username" in data and data["username"] != user.username:
            if UserService.get_by_username(db, data["username"]):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Username already taken",
                )

        for field, value in data.items():
            setattr(user, field, value)

        if password:
            user.hashed_password = hash_password(password)

        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def delete_user(db: Session, user: User) -> None:
        db.delete(user)
        db.commit()
