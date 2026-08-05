from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.domain.entities.user import UserRole
from app.domain.errors import BusinessRuleViolation, DomainValidationError

from ..dependencies import get_dataset_service, require_roles
from ..responses import success

router = APIRouter(tags=["datasets"])

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


def _dataset_dict(d: Any) -> dict[str, Any]:
    return {
        "id": str(d.id),
        "name": d.name,
        "status": d.status.value if hasattr(d.status, "value") else d.status,
        "fingerprint_count": d.fingerprint_count,
        "observation_count": d.observation_count,
        "floor_count": d.floor_count,
        "dataset_version": d.dataset_version,
        "version": d.version,
        "is_active": d.is_active,
        "created_at": d.created_at.isoformat(),
        "updated_at": d.updated_at.isoformat(),
    }


@router.get("/datasets")
def list_datasets(
    service: Any = Depends(get_dataset_service),
) -> dict[str, Any]:
    items = service.list_all()
    return success(data=[_dataset_dict(d) for d in items])


@router.get("/datasets/{dataset_id}")
def get_dataset(
    dataset_id: UUID,
    service: Any = Depends(get_dataset_service),
) -> dict[str, Any]:
    try:
        entity = service.get(dataset_id)
    except LookupError as exc:
        raise _handle_domain_errors(exc)
    return success(data=_dataset_dict(entity))


@router.post(
    "/datasets",
    status_code=status.HTTP_201_CREATED,
)
def create_dataset(
    body: dict[str, Any],
    _user: Any = Depends(OperatorOrAdmin),
    service: Any = Depends(get_dataset_service),
) -> dict[str, Any]:
    try:
        entity = service.create(name=body["name"])
    except DomainValidationError as exc:
        raise _handle_domain_errors(exc)
    return success(data=_dataset_dict(entity), message="Dataset created.")


@router.patch("/datasets/{dataset_id}/add-campaigns")
def add_campaigns(
    dataset_id: UUID,
    body: dict[str, Any],
    _user: Any = Depends(OperatorOrAdmin),
    service: Any = Depends(get_dataset_service),
) -> dict[str, Any]:
    try:
        campaign_ids = [UUID(cid) for cid in body["campaign_ids"]]
        entity = service.add_campaigns(dataset_id, campaign_ids)
    except (LookupError, BusinessRuleViolation, DomainValidationError) as exc:
        raise _handle_domain_errors(exc)
    return success(data=_dataset_dict(entity))


@router.patch("/datasets/{dataset_id}/build")
def build_dataset(
    dataset_id: UUID,
    _user: Any = Depends(OperatorOrAdmin),
    service: Any = Depends(get_dataset_service),
) -> dict[str, Any]:
    try:
        entity = service.build(dataset_id)
    except (LookupError, BusinessRuleViolation) as exc:
        raise _handle_domain_errors(exc)
    return success(data=_dataset_dict(entity))


@router.patch("/datasets/{dataset_id}/archive")
def archive_dataset(
    dataset_id: UUID,
    _user: Any = Depends(OperatorOrAdmin),
    service: Any = Depends(get_dataset_service),
) -> dict[str, Any]:
    try:
        entity = service.archive(dataset_id)
    except (LookupError, BusinessRuleViolation) as exc:
        raise _handle_domain_errors(exc)
    return success(data=_dataset_dict(entity))


@router.delete("/datasets/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dataset(
    dataset_id: UUID,
    _user: Any = Depends(Administrator),
    service: Any = Depends(get_dataset_service),
) -> None:
    try:
        service.soft_delete(dataset_id)
    except (LookupError, BusinessRuleViolation) as exc:
        raise _handle_domain_errors(exc)
