from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db
from app.models.user import User
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from app.schemas.user import UserRead
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    responses={
        201: {"description": "User registered and tokens issued"},
        409: {"description": "Email or username already exists"},
    },
)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> AuthResponse:
    user, tokens = AuthService.register(db, payload)
    return AuthResponse(user=UserRead.model_validate(user), tokens=tokens)


@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Login with email and password",
    responses={
        200: {"description": "Login successful"},
        401: {"description": "Invalid credentials"},
    },
)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> AuthResponse:
    user, tokens = AuthService.login(db, payload)
    return AuthResponse(user=UserRead.model_validate(user), tokens=tokens)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
    responses={
        200: {"description": "New access and refresh tokens issued"},
        401: {"description": "Invalid or expired refresh token"},
    },
)
def refresh_tokens(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    return AuthService.refresh_access_token(db, payload.refresh_token)


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Logout (revoke refresh token)",
)
def logout(payload: LogoutRequest, db: Session = Depends(get_db)) -> MessageResponse:
    AuthService.logout(db, payload.refresh_token)
    return MessageResponse(message="Logged out successfully")


@router.get(
    "/me",
    response_model=UserRead,
    summary="Get current authenticated user",
    responses={
        200: {"description": "Current user profile"},
        401: {"description": "Not authenticated"},
    },
)
def get_me(current_user: User = Depends(get_current_active_user)) -> UserRead:
    return UserRead.model_validate(current_user)
