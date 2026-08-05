from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.domain.entities.user import UserRole
from app.domain.errors import BusinessRuleViolation, DomainValidationError

from ..dependencies import get_campaign_service, require_roles
from ..responses import success

router = APIRouter(tags=["campaigns"])

Administrator = require_roles(UserRole.ADMINISTRATOR)
OperatorOrAdmin = require_roles(UserRole.ADMINISTRATOR, UserRole.OPERATOR)


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


def _campaign_dict(c: Any) -> dict[str, Any]:
    return {
        "id": str(c.id),
        "floor_id": str(c.floor_id),
        "name": c.name,
        "status": c.status.value,
        "started_at": c.started_at.isoformat() if c.started_at else None,
        "finished_at": c.finished_at.isoformat() if c.finished_at else None,
        "version": c.version,
        "is_active": c.is_active,
        "created_at": c.created_at.isoformat(),
        "updated_at": c.updated_at.isoformat(),
    }


@router.get("/campaigns")
def list_all_campaigns(
    service: Any = Depends(get_campaign_service),
) -> dict[str, Any]:
    items = service.list_all()
    return success(data=[_campaign_dict(c) for c in items])


@router.get("/floors/{floor_id}/campaigns")
def list_campaigns(
    floor_id: UUID,
    service: Any = Depends(get_campaign_service),
) -> dict[str, Any]:
    try:
        items = service.list_by_floor(floor_id)
    except LookupError as exc:
        raise _handle_domain_errors(exc)
    return success(data=[_campaign_dict(c) for c in items])


@router.get("/campaigns/{campaign_id}")
def get_campaign(
    campaign_id: UUID,
    service: Any = Depends(get_campaign_service),
) -> dict[str, Any]:
    try:
        entity = service.get(campaign_id)
    except LookupError as exc:
        raise _handle_domain_errors(exc)
    return success(data=_campaign_dict(entity))


@router.post(
    "/floors/{floor_id}/campaigns",
    status_code=status.HTTP_201_CREATED,
)
def create_campaign(
    floor_id: UUID,
    body: dict[str, Any],
    _user: Any = Depends(OperatorOrAdmin),
    service: Any = Depends(get_campaign_service),
) -> dict[str, Any]:
    try:
        entity = service.create(floor_id=floor_id, name=body["name"])
    except (LookupError, DomainValidationError) as exc:
        raise _handle_domain_errors(exc)
    return success(data=_campaign_dict(entity), message="Campaign created.")


@router.patch("/campaigns/{campaign_id}/start")
def start_campaign(
    campaign_id: UUID,
    _user: Any = Depends(OperatorOrAdmin),
    service: Any = Depends(get_campaign_service),
) -> dict[str, Any]:
    try:
        entity = service.start(campaign_id)
    except (LookupError, BusinessRuleViolation) as exc:
        raise _handle_domain_errors(exc)
    return success(data=_campaign_dict(entity))


@router.patch("/campaigns/{campaign_id}/begin-collecting")
def begin_collecting(
    campaign_id: UUID,
    _user: Any = Depends(OperatorOrAdmin),
    service: Any = Depends(get_campaign_service),
) -> dict[str, Any]:
    try:
        entity = service.begin_collecting(campaign_id)
    except (LookupError, BusinessRuleViolation) as exc:
        raise _handle_domain_errors(exc)
    return success(data=_campaign_dict(entity))


@router.patch("/campaigns/{campaign_id}/pause")
def pause_campaign(
    campaign_id: UUID,
    _user: Any = Depends(OperatorOrAdmin),
    service: Any = Depends(get_campaign_service),
) -> dict[str, Any]:
    try:
        entity = service.pause(campaign_id)
    except (LookupError, BusinessRuleViolation) as exc:
        raise _handle_domain_errors(exc)
    return success(data=_campaign_dict(entity))


@router.patch("/campaigns/{campaign_id}/resume")
def resume_campaign(
    campaign_id: UUID,
    _user: Any = Depends(OperatorOrAdmin),
    service: Any = Depends(get_campaign_service),
) -> dict[str, Any]:
    try:
        entity = service.resume(campaign_id)
    except (LookupError, BusinessRuleViolation) as exc:
        raise _handle_domain_errors(exc)
    return success(data=_campaign_dict(entity))


@router.patch("/campaigns/{campaign_id}/complete")
def complete_campaign(
    campaign_id: UUID,
    _user: Any = Depends(OperatorOrAdmin),
    service: Any = Depends(get_campaign_service),
) -> dict[str, Any]:
    try:
        entity = service.complete(campaign_id)
    except (LookupError, BusinessRuleViolation) as exc:
        raise _handle_domain_errors(exc)
    return success(data=_campaign_dict(entity))


@router.patch("/campaigns/{campaign_id}/archive")
def archive_campaign(
    campaign_id: UUID,
    _user: Any = Depends(OperatorOrAdmin),
    service: Any = Depends(get_campaign_service),
) -> dict[str, Any]:
    try:
        entity = service.archive(campaign_id)
    except (LookupError, BusinessRuleViolation) as exc:
        raise _handle_domain_errors(exc)
    return success(data=_campaign_dict(entity))


@router.delete("/campaigns/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_campaign(
    campaign_id: UUID,
    _user: Any = Depends(Administrator),
    service: Any = Depends(get_campaign_service),
) -> None:
    try:
        service.soft_delete(campaign_id)
    except (LookupError, BusinessRuleViolation) as exc:
        raise _handle_domain_errors(exc)
