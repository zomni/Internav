from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.application.floor_plan_service import FloorPlanService
from app.application.grid_service import GridService
from app.application.svg_analyzer import compute_walkability
from app.domain.entities.user import UserRole
from app.domain.errors import BusinessRuleViolation, DomainValidationError

from ..dependencies import get_floor_plan_service, get_grid_service, require_roles
from ..responses import success

router = APIRouter(tags=["grids"])

Administrator = require_roles(UserRole.ADMINISTRATOR)
OperatorOrAdmin = require_roles(UserRole.ADMINISTRATOR, UserRole.OPERATOR)


class GridGenerateRequest(BaseModel):
    name: str
    cell_size: int = Field(gt=0)
    analyze_walkability: bool = False


class WalkableUpdateRequest(BaseModel):
    walkable: bool


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


def _grid_dict(g: Any) -> dict[str, Any]:
    return {
        "id": str(g.id),
        "floor_id": str(g.floor_id),
        "name": g.name,
        "cell_size": g.cell_size,
        "status": g.status.value if hasattr(g.status, "value") else g.status,
        "version": g.version,
        "is_active": g.is_active,
        "created_at": g.created_at.isoformat(),
        "updated_at": g.updated_at.isoformat(),
    }


def _cell_dict(c: Any) -> dict[str, Any]:
    return {
        "id": str(c.id),
        "grid_id": str(c.grid_id),
        "row": c.row,
        "column": c.column,
        "center_x": c.center_x,
        "center_y": c.center_y,
        "walkable": c.walkable,
        "version": c.version,
        "is_active": c.is_active,
        "created_at": c.created_at.isoformat(),
        "updated_at": c.updated_at.isoformat(),
    }


def _plan_walkability_mask(
    floor_plan_service: FloorPlanService,
    floor_id: UUID,
    cell_size: int,
) -> list[bool]:
    plan = floor_plan_service.get_active(floor_id)
    if plan is None:
        raise BusinessRuleViolation("An active FloorPlan is required to analyze walkability.")
    if plan.mime_type != "image/svg+xml":
        raise DomainValidationError("Walkability analysis requires an SVG floor plan.")
    path = Path(plan.image_path)
    if not path.is_file():
        raise DomainValidationError("Active FloorPlan image file is missing.")
    mask = compute_walkability(
        svg_bytes=path.read_bytes(),
        width=plan.width,
        height=plan.height,
        cell_size=cell_size,
    )
    return mask.walkable


@router.get("/grids")
def list_all_grids(
    service: Any = Depends(get_grid_service),
) -> dict[str, Any]:
    items = service.list_all()
    return success(data=[_grid_dict(g) for g in items])


@router.get("/floors/{floor_id}/grids")
def list_grids(
    floor_id: UUID,
    service: Any = Depends(get_grid_service),
) -> dict[str, Any]:
    try:
        items = service.list_by_floor(floor_id)
    except LookupError as exc:
        raise _handle_domain_errors(exc)
    return success(data=[_grid_dict(g) for g in items])


@router.post(
    "/floors/{floor_id}/grids",
    status_code=status.HTTP_201_CREATED,
)
def generate_grid(
    floor_id: UUID,
    body: GridGenerateRequest,
    _user: Any = Depends(OperatorOrAdmin),
    service: GridService = Depends(get_grid_service),
    floor_plan_service: FloorPlanService = Depends(get_floor_plan_service),
) -> dict[str, Any]:
    try:
        walkable_mask = (
            _plan_walkability_mask(floor_plan_service, floor_id, body.cell_size)
            if body.analyze_walkability
            else None
        )
        entity = service.generate(
            floor_id=floor_id,
            name=body.name,
            cell_size=body.cell_size,
            walkable_mask=walkable_mask,
        )
    except (LookupError, DomainValidationError, BusinessRuleViolation) as exc:
        raise _handle_domain_errors(exc)
    return success(data=_grid_dict(entity), message="Grid generated.")


@router.get("/grids/{entity_id}")
def get_grid(
    entity_id: UUID,
    service: Any = Depends(get_grid_service),
) -> dict[str, Any]:
    try:
        entity = service.get(entity_id)
    except LookupError as exc:
        raise _handle_domain_errors(exc)
    return success(data=_grid_dict(entity))


@router.post("/grids/{entity_id}/regenerate")
def regenerate_grid(
    entity_id: UUID,
    _user: Any = Depends(OperatorOrAdmin),
    service: Any = Depends(get_grid_service),
) -> dict[str, Any]:
    try:
        entity = service.regenerate(entity_id)
    except (LookupError, BusinessRuleViolation) as exc:
        raise _handle_domain_errors(exc)
    return success(data=_grid_dict(entity), message="Grid regenerated.")


@router.post("/grids/{entity_id}/activate")
def activate_grid(
    entity_id: UUID,
    _user: Any = Depends(OperatorOrAdmin),
    service: Any = Depends(get_grid_service),
) -> dict[str, Any]:
    try:
        entity = service.activate(entity_id)
    except (LookupError, BusinessRuleViolation) as exc:
        raise _handle_domain_errors(exc)
    return success(data=_grid_dict(entity), message="Grid activated.")


@router.post("/grids/{entity_id}/lock")
def lock_grid(
    entity_id: UUID,
    _user: Any = Depends(OperatorOrAdmin),
    service: Any = Depends(get_grid_service),
) -> dict[str, Any]:
    try:
        entity = service.lock(entity_id)
    except (LookupError, BusinessRuleViolation) as exc:
        raise _handle_domain_errors(exc)
    return success(data=_grid_dict(entity), message="Grid locked.")


@router.post("/grids/{entity_id}/unlock")
def unlock_grid(
    entity_id: UUID,
    _user: Any = Depends(OperatorOrAdmin),
    service: Any = Depends(get_grid_service),
) -> dict[str, Any]:
    try:
        entity = service.unlock(entity_id)
    except (LookupError, BusinessRuleViolation) as exc:
        raise _handle_domain_errors(exc)
    return success(data=_grid_dict(entity), message="Grid unlocked.")


@router.get("/grids/{entity_id}/cells")
def list_cells(
    entity_id: UUID,
    service: Any = Depends(get_grid_service),
) -> dict[str, Any]:
    try:
        items = service.list_cells(entity_id)
    except LookupError as exc:
        raise _handle_domain_errors(exc)
    return success(data=[_cell_dict(c) for c in items])


@router.put("/cells/{cell_id}/walkable")
def update_walkable(
    cell_id: UUID,
    body: WalkableUpdateRequest,
    _user: Any = Depends(OperatorOrAdmin),
    service: Any = Depends(get_grid_service),
) -> dict[str, Any]:
    try:
        entity = service.update_walkable(cell_id, body.walkable)
    except (LookupError, BusinessRuleViolation) as exc:
        raise _handle_domain_errors(exc)
    return success(data=_cell_dict(entity), message="Cell walkable updated.")


@router.delete("/grids/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_grid(
    entity_id: UUID,
    _user: Any = Depends(Administrator),
    service: Any = Depends(get_grid_service),
) -> None:
    try:
        service.soft_delete(entity_id)
    except (LookupError, BusinessRuleViolation) as exc:
        raise _handle_domain_errors(exc)
