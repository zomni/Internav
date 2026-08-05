from collections.abc import Sequence
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.application.core_hierarchy_service import CoreHierarchyService
from app.domain.entities.user import UserRole
from app.domain.errors import BusinessRuleViolation, DomainValidationError
from app.schemas.hierarchy import (
    BuildingCreateRequest,
    BuildingUpdateRequest,
    FloorCreateRequest,
    FloorUpdateRequest,
    OrganizationCreateRequest,
    OrganizationUpdateRequest,
    PageQuery,
    SiteCreateRequest,
    SiteUpdateRequest,
)

from ..dependencies import get_hierarchy_service, require_roles
from ..responses import success

router = APIRouter(tags=["hierarchy"])

Administrator = require_roles(UserRole.ADMINISTRATOR)
OperatorOrAdmin = require_roles(UserRole.ADMINISTRATOR, UserRole.OPERATOR)


def _entity_to_dict(entity: object) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for key in (
        "id",
        "name",
        "code",
        "description",
        "timezone",
        "address",
        "metadata",
        "level",
        "display_order",
        "organization_id",
        "site_id",
        "building_id",
        "is_active",
        "created_at",
        "updated_at",
    ):
        value = getattr(entity, key, None)
        if value is not None:
            data[key] = str(value) if isinstance(value, UUID) else value
    return data


def _paginate(items: Sequence[object], query: PageQuery) -> dict[str, Any]:
    total = len(items)
    start = (query.page - 1) * query.page_size
    end = start + query.page_size
    page_items = items[start:end]
    return {
        "items": [_entity_to_dict(i) for i in page_items],
        "total": total,
        "page": query.page,
        "page_size": query.page_size,
    }


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


# ── Organizations ──────────────────────────────────────────────


@router.get("/organizations")
def list_organizations(
    service: CoreHierarchyService = Depends(get_hierarchy_service),
) -> dict[str, Any]:
    items = service.list_organizations()
    return success(data=[_entity_to_dict(i) for i in items])


@router.post("/organizations", status_code=status.HTTP_201_CREATED)
def create_organization(
    body: OrganizationCreateRequest,
    _user: object = Depends(OperatorOrAdmin),
    service: CoreHierarchyService = Depends(get_hierarchy_service),
) -> dict[str, Any]:
    try:
        entity = service.create_organization(
            name=body.name, code=body.code, description=body.description
        )
    except (DomainValidationError, ValueError) as exc:
        raise _handle_domain_errors(exc)
    return success(data=_entity_to_dict(entity), message="Organization created.")


@router.get("/organizations/{entity_id}")
def get_organization(
    entity_id: UUID,
    service: CoreHierarchyService = Depends(get_hierarchy_service),
) -> dict[str, Any]:
    try:
        entity = service.get_organization(entity_id)
    except LookupError as exc:
        raise _handle_domain_errors(exc)
    return success(data=_entity_to_dict(entity))


@router.put("/organizations/{entity_id}")
def update_organization(
    entity_id: UUID,
    body: OrganizationUpdateRequest,
    _user: object = Depends(OperatorOrAdmin),
    service: CoreHierarchyService = Depends(get_hierarchy_service),
) -> dict[str, Any]:
    changes = body.model_dump(exclude_unset=True)
    try:
        entity = service.update_organization(entity_id, **changes)
    except (LookupError, DomainValidationError, ValueError) as exc:
        raise _handle_domain_errors(exc)
    return success(data=_entity_to_dict(entity), message="Organization updated.")


@router.delete("/organizations/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_organization(
    entity_id: UUID,
    _user: object = Depends(Administrator),
    service: CoreHierarchyService = Depends(get_hierarchy_service),
) -> None:
    try:
        service.delete_organization(entity_id)
    except (LookupError, BusinessRuleViolation) as exc:
        raise _handle_domain_errors(exc)


# ── Sites ──────────────────────────────────────────────────────


@router.get("/sites")
def list_sites(
    service: CoreHierarchyService = Depends(get_hierarchy_service),
) -> dict[str, Any]:
    items = service.list_sites()
    return success(data=[_entity_to_dict(i) for i in items])


@router.post("/sites", status_code=status.HTTP_201_CREATED)
def create_site(
    body: SiteCreateRequest,
    _user: object = Depends(OperatorOrAdmin),
    service: CoreHierarchyService = Depends(get_hierarchy_service),
) -> dict[str, Any]:
    try:
        entity = service.create_site(
            organization_id=body.organization_id,
            name=body.name,
            code=body.code,
            timezone=body.timezone,
            address=body.address,
            metadata=body.metadata,
        )
    except (LookupError, DomainValidationError, ValueError) as exc:
        raise _handle_domain_errors(exc)
    return success(data=_entity_to_dict(entity), message="Site created.")


@router.get("/sites/{entity_id}")
def get_site(
    entity_id: UUID,
    service: CoreHierarchyService = Depends(get_hierarchy_service),
) -> dict[str, Any]:
    try:
        entity = service.get_site(entity_id)
    except LookupError as exc:
        raise _handle_domain_errors(exc)
    return success(data=_entity_to_dict(entity))


@router.put("/sites/{entity_id}")
def update_site(
    entity_id: UUID,
    body: SiteUpdateRequest,
    _user: object = Depends(OperatorOrAdmin),
    service: CoreHierarchyService = Depends(get_hierarchy_service),
) -> dict[str, Any]:
    changes = body.model_dump(exclude_unset=True)
    try:
        entity = service.update_site(entity_id, **changes)
    except (LookupError, DomainValidationError, ValueError) as exc:
        raise _handle_domain_errors(exc)
    return success(data=_entity_to_dict(entity), message="Site updated.")


@router.delete("/sites/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_site(
    entity_id: UUID,
    _user: object = Depends(Administrator),
    service: CoreHierarchyService = Depends(get_hierarchy_service),
) -> None:
    try:
        service.delete_site(entity_id)
    except (LookupError, BusinessRuleViolation) as exc:
        raise _handle_domain_errors(exc)


# ── Buildings ──────────────────────────────────────────────────


@router.get("/buildings")
def list_buildings(
    service: CoreHierarchyService = Depends(get_hierarchy_service),
) -> dict[str, Any]:
    items = service.list_buildings()
    return success(data=[_entity_to_dict(i) for i in items])


@router.post("/buildings", status_code=status.HTTP_201_CREATED)
def create_building(
    body: BuildingCreateRequest,
    _user: object = Depends(OperatorOrAdmin),
    service: CoreHierarchyService = Depends(get_hierarchy_service),
) -> dict[str, Any]:
    try:
        entity = service.create_building(
            site_id=body.site_id, name=body.name, code=body.code, description=body.description
        )
    except (LookupError, DomainValidationError, ValueError) as exc:
        raise _handle_domain_errors(exc)
    return success(data=_entity_to_dict(entity), message="Building created.")


@router.get("/buildings/{entity_id}")
def get_building(
    entity_id: UUID,
    service: CoreHierarchyService = Depends(get_hierarchy_service),
) -> dict[str, Any]:
    try:
        entity = service.get_building(entity_id)
    except LookupError as exc:
        raise _handle_domain_errors(exc)
    return success(data=_entity_to_dict(entity))


@router.put("/buildings/{entity_id}")
def update_building(
    entity_id: UUID,
    body: BuildingUpdateRequest,
    _user: object = Depends(OperatorOrAdmin),
    service: CoreHierarchyService = Depends(get_hierarchy_service),
) -> dict[str, Any]:
    changes = body.model_dump(exclude_unset=True)
    try:
        entity = service.update_building(entity_id, **changes)
    except (LookupError, DomainValidationError, ValueError) as exc:
        raise _handle_domain_errors(exc)
    return success(data=_entity_to_dict(entity), message="Building updated.")


@router.delete("/buildings/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_building(
    entity_id: UUID,
    _user: object = Depends(Administrator),
    service: CoreHierarchyService = Depends(get_hierarchy_service),
) -> None:
    try:
        service.delete_building(entity_id)
    except (LookupError, BusinessRuleViolation) as exc:
        raise _handle_domain_errors(exc)


# ── Floors ─────────────────────────────────────────────────────


@router.get("/floors")
def list_floors(
    service: CoreHierarchyService = Depends(get_hierarchy_service),
) -> dict[str, Any]:
    items = service.list_floors()
    return success(data=[_entity_to_dict(i) for i in items])


@router.post("/floors", status_code=status.HTTP_201_CREATED)
def create_floor(
    body: FloorCreateRequest,
    _user: object = Depends(OperatorOrAdmin),
    service: CoreHierarchyService = Depends(get_hierarchy_service),
) -> dict[str, Any]:
    try:
        entity = service.create_floor(
            building_id=body.building_id,
            name=body.name,
            level=body.level,
            display_order=body.display_order,
        )
    except (LookupError, DomainValidationError, ValueError) as exc:
        raise _handle_domain_errors(exc)
    return success(data=_entity_to_dict(entity), message="Floor created.")


@router.get("/floors/{entity_id}")
def get_floor(
    entity_id: UUID,
    service: CoreHierarchyService = Depends(get_hierarchy_service),
) -> dict[str, Any]:
    try:
        entity = service.get_floor(entity_id)
    except LookupError as exc:
        raise _handle_domain_errors(exc)
    return success(data=_entity_to_dict(entity))


@router.put("/floors/{entity_id}")
def update_floor(
    entity_id: UUID,
    body: FloorUpdateRequest,
    _user: object = Depends(OperatorOrAdmin),
    service: CoreHierarchyService = Depends(get_hierarchy_service),
) -> dict[str, Any]:
    changes = body.model_dump(exclude_unset=True)
    try:
        entity = service.update_floor(entity_id, **changes)
    except (LookupError, DomainValidationError, ValueError) as exc:
        raise _handle_domain_errors(exc)
    return success(data=_entity_to_dict(entity), message="Floor updated.")


@router.delete("/floors/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_floor(
    entity_id: UUID,
    _user: object = Depends(Administrator),
    service: CoreHierarchyService = Depends(get_hierarchy_service),
) -> None:
    try:
        service.delete_floor(entity_id)
    except (LookupError, BusinessRuleViolation) as exc:
        raise _handle_domain_errors(exc)
