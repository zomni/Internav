from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt

from app.config.settings import Settings
from app.domain.entities.user import User, UserRole


class TokenValidationError(ValueError):
    """Raised when a JWT cannot be used for the requested purpose."""


def _encode(user: User, token_type: str, expires_at: datetime, settings: Settings) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": str(user.id),
            "role": user.role.value,
            "type": token_type,
            "iat": now,
            "exp": expires_at,
        },
        settings.jwt_secret_key,
        algorithm="HS256",
    )


def create_access_token(user: User, settings: Settings) -> str:
    return _encode(
        user,
        "access",
        datetime.now(UTC) + timedelta(minutes=settings.jwt_access_token_minutes),
        settings,
    )


def create_refresh_token(user: User, settings: Settings) -> str:
    return _encode(
        user,
        "refresh",
        datetime.now(UTC) + timedelta(days=settings.jwt_refresh_token_days),
        settings,
    )


def decode_token(token: str, expected_type: str, settings: Settings) -> tuple[UUID, UserRole]:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=["HS256"])
        if payload.get("type") != expected_type:
            raise TokenValidationError("Unexpected token type.")
        return UUID(payload["sub"]), UserRole(payload["role"])
    except (jwt.PyJWTError, KeyError, ValueError) as error:
        raise TokenValidationError("Invalid or expired token.") from error
