from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.application.auth_service import AuthenticationError, AuthService
from app.infrastructure.persistence.repositories.user_sqlalchemy_repository import (
    SqlAlchemyUserRepository,
)
from app.schemas.auth import LoginRequest, RefreshTokenRequest
from app.security.tokens import (
    TokenValidationError,
    create_access_token,
    create_refresh_token,
    decode_token,
)

from ..dependencies import get_session
from ..responses import success

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
def login(
    body: LoginRequest, request: Request, session: Session = Depends(get_session)
) -> dict[str, Any]:
    auth_service = AuthService(SqlAlchemyUserRepository(session), request.app.state.settings)
    try:
        access_token, refresh_token, user = auth_service.authenticate(body.email, body.password)
    except AuthenticationError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(error)) from error
    return success(
        data={
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": {
                "id": str(user.id),
                "email": user.email,
                "role": user.role.value,
            },
        },
        message="Login successful.",
    )


@router.post("/refresh")
def refresh_token(
    body: RefreshTokenRequest, request: Request, session: Session = Depends(get_session)
) -> dict[str, Any]:
    settings = request.app.state.settings
    try:
        user_id, _ = decode_token(body.refresh_token, "refresh", settings)
    except TokenValidationError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(error)) from error
    user_repo = SqlAlchemyUserRepository(session)
    user = user_repo.get(UUID(str(user_id)))
    if user is None or not user.is_active or user.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User is inactive.")
    access_token = create_access_token(user, settings)
    new_refresh_token = create_refresh_token(user, settings)
    return success(
        data={
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
        },
        message="Token refreshed.",
    )
