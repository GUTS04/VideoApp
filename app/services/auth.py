import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    create_refresh_token_value,
    hash_token,
    verify_password,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserCreate
from app.services.user import UserService


class AuthService:
    @staticmethod
    def register(db: Session, payload: RegisterRequest) -> tuple[User, TokenResponse]:
        user = UserService.create_user(
            db,
            UserCreate(
                email=payload.email,
                username=payload.username,
                password=payload.password,
                gender=payload.gender,
            ),
        )
        tokens = AuthService.issue_tokens(db, user)
        return user, tokens

    @staticmethod
    def login(db: Session, payload: LoginRequest) -> tuple[User, TokenResponse]:
        user = UserService.get_by_email(db, payload.email)
        if not user or not verify_password(payload.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Inactive user account",
            )
        tokens = AuthService.issue_tokens(db, user)
        return user, tokens

    @staticmethod
    def refresh_access_token(db: Session, refresh_token: str) -> TokenResponse:
        token_hash = hash_token(refresh_token)
        record = db.scalar(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked.is_(False),
            )
        )
        if not record or record.expires_at < datetime.now(UTC):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
            )

        user = UserService.get_by_id(db, record.user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
            )

        record.revoked = True
        db.commit()
        return AuthService.issue_tokens(db, user)

    @staticmethod
    def logout(db: Session, refresh_token: str) -> None:
        token_hash = hash_token(refresh_token)
        record = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
        if record:
            record.revoked = True
            db.commit()

    @staticmethod
    def issue_tokens(db: Session, user: User) -> TokenResponse:
        settings = get_settings()
        access_token, expires_in = create_access_token(user_id=str(user.id))

        refresh_value = create_refresh_token_value()
        expires_at = datetime.now(UTC) + timedelta(days=settings.jwt_refresh_token_expire_days)
        db.add(
            RefreshToken(
                user_id=user.id,
                token_hash=hash_token(refresh_value),
                expires_at=expires_at,
            )
        )
        db.commit()

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_value,
            expires_in=expires_in,
        )

    @staticmethod
    def get_refresh_token_record(db: Session, refresh_token: str) -> RefreshToken | None:
        return db.scalar(
            select(RefreshToken).where(RefreshToken.token_hash == hash_token(refresh_token))
        )
