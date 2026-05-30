from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.user import UserRead

REGISTER_EXAMPLE = {
    "email": "demo@example.com",
    "username": "demouser",
    "password": "SecurePass123!",
    "gender": "male",
}

LOGIN_EXAMPLE = {
    "email": "demo@example.com",
    "password": "SecurePass123!",
}

REFRESH_EXAMPLE = {
    "refresh_token": "paste-refresh-token-from-login-response",
}

LOGOUT_EXAMPLE = {
    "refresh_token": "paste-refresh-token-from-login-response",
}


class RegisterRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"examples": [REGISTER_EXAMPLE]},
    )

    email: EmailStr
    username: str = Field(..., min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_]+$")
    password: str = Field(..., min_length=8, max_length=128)
    gender: Literal["male", "female"] = Field(
        ...,
        description="male matches female; female matches male",
        examples=["male"],
    )


class LoginRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"examples": [LOGIN_EXAMPLE]},
    )

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class RefreshRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"examples": [REFRESH_EXAMPLE]},
    )

    refresh_token: str = Field(..., min_length=10)


class LogoutRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"examples": [LOGOUT_EXAMPLE]},
    )

    refresh_token: str = Field(..., min_length=10)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Access token lifetime in seconds")


class AuthResponse(BaseModel):
    user: UserRead
    tokens: TokenResponse


class MessageResponse(BaseModel):
    message: str
