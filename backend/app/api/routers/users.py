from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.domain.entities.user import UserRole
from app.domain.errors import BusinessRuleViolation, DomainValidationError

from ..dependencies import get_user_service, require_roles
from ..responses import success

router = APIRouter(tags=["users"])

Administrator = require_roles(UserRole.ADMINISTRATOR)


def _handle_domain_errors(exc: Exception) -> HTTPException:
    if isinstance(exc, LookupError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, BusinessRuleViolation):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if isinstance(exc, DomainValidationError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal error."
    )


def _user_dict(u: Any) -> dict[str, Any]:
    return {
        "id": str(u.id),
        "email": u.email,
        "role": u.role.value if hasattr(u.role, "value") else u.role,
        "organization_id": str(u.organization_id) if u.organization_id else None,
        "is_active": u.is_active,
        "created_at": u.created_at.isoformat(),
        "updated_at": u.updated_at.isoformat(),
    }


@router.get("/users")
def list_users(
    _user: Any = Depends(Administrator),
    service: Any = Depends(get_user_service),
) -> dict[str, Any]:
    items = service.list_all()
    return success(data=[_user_dict(u) for u in items])


@router.get("/users/{user_id}")
def get_user(
    user_id: UUID,
    _user: Any = Depends(Administrator),
    service: Any = Depends(get_user_service),
) -> dict[str, Any]:
    try:
        entity = service.get(user_id)
    except LookupError as exc:
        raise _handle_domain_errors(exc)
    return success(data=_user_dict(entity))


@router.post(
    "/users",
    status_code=status.HTTP_201_CREATED,
)
def create_user(
    body: dict[str, Any],
    _user: Any = Depends(Administrator),
    service: Any = Depends(get_user_service),
) -> dict[str, Any]:
    try:
        entity = service.create(
            email=body["email"],
            password=body["password"],
            role=UserRole(body["role"]),
            organization_id=UUID(body["organization_id"]) if body.get("organization_id") else None,
        )
    except (BusinessRuleViolation, DomainValidationError) as exc:
        raise _handle_domain_errors(exc)
    return success(data=_user_dict(entity), message="User created.")


@router.patch("/users/{user_id}/role")
def update_role(
    user_id: UUID,
    body: dict[str, Any],
    _user: Any = Depends(Administrator),
    service: Any = Depends(get_user_service),
) -> dict[str, Any]:
    try:
        entity = service.update_role(user_id, UserRole(body["role"]))
    except (LookupError, BusinessRuleViolation, DomainValidationError) as exc:
        raise _handle_domain_errors(exc)
    return success(data=_user_dict(entity))


@router.patch("/users/{user_id}/password")
def update_password(
    user_id: UUID,
    body: dict[str, Any],
    _user: Any = Depends(Administrator),
    service: Any = Depends(get_user_service),
) -> dict[str, Any]:
    try:
        entity = service.update_password(user_id, body["new_password"])
    except (LookupError, DomainValidationError) as exc:
        raise _handle_domain_errors(exc)
    return success(data=_user_dict(entity), message="Password updated.")


@router.patch("/users/{user_id}/deactivate")
def deactivate_user(
    user_id: UUID,
    _user: Any = Depends(Administrator),
    service: Any = Depends(get_user_service),
) -> dict[str, Any]:
    try:
        entity = service.deactivate(user_id)
    except LookupError as exc:
        raise _handle_domain_errors(exc)
    return success(data=_user_dict(entity))


@router.patch("/users/{user_id}/activate")
def activate_user(
    user_id: UUID,
    _user: Any = Depends(Administrator),
    service: Any = Depends(get_user_service),
) -> dict[str, Any]:
    try:
        entity = service.activate(user_id)
    except LookupError as exc:
        raise _handle_domain_errors(exc)
    return success(data=_user_dict(entity))


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: UUID,
    _user: Any = Depends(Administrator),
    service: Any = Depends(get_user_service),
) -> None:
    try:
        service.soft_delete(user_id)
    except (LookupError, BusinessRuleViolation) as exc:
        raise _handle_domain_errors(exc)
