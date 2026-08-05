from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from app.application.svg_analyzer import parse_svg_dimensions
from app.domain.entities.user import UserRole
from app.domain.errors import BusinessRuleViolation, DomainValidationError

from ..dependencies import get_floor_plan_service, require_roles
from ..responses import success

router = APIRouter(tags=["floor-plans"])

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


def _fp_dict(fp: Any) -> dict[str, Any]:
    return {
        "id": str(fp.id),
        "floor_id": str(fp.floor_id),
        "image_path": fp.image_path,
        "width": fp.width,
        "height": fp.height,
        "scale": fp.scale,
        "checksum": fp.checksum,
        "mime_type": fp.mime_type,
        "version": fp.version,
        "is_active": fp.is_active,
        "created_at": fp.created_at.isoformat(),
        "updated_at": fp.updated_at.isoformat(),
    }


@router.get("/floors/{floor_id}/floor-plans")
def list_floor_plans(
    floor_id: UUID,
    service: Any = Depends(get_floor_plan_service),
) -> dict[str, Any]:
    try:
        items = service.list_by_floor(floor_id)
    except LookupError as exc:
        raise _handle_domain_errors(exc)
    return success(data=[_fp_dict(fp) for fp in items])


@router.get("/floor-plans/{entity_id}")
def get_floor_plan(
    entity_id: UUID,
    service: Any = Depends(get_floor_plan_service),
) -> dict[str, Any]:
    try:
        entity = service.get(entity_id)
    except LookupError as exc:
        raise _handle_domain_errors(exc)
    return success(data=_fp_dict(entity))


@router.get("/floor-plans/{entity_id}/image")
def get_floor_plan_image(
    entity_id: UUID,
    service: Any = Depends(get_floor_plan_service),
) -> FileResponse:
    try:
        entity = service.get(entity_id)
    except LookupError as exc:
        raise _handle_domain_errors(exc)
    path = Path(entity.image_path)
    if not path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="FloorPlan image not found."
        )
    return FileResponse(str(path), media_type=entity.mime_type, filename=path.name)


@router.post(
    "/floors/{floor_id}/floor-plans",
    status_code=status.HTTP_201_CREATED,
)
async def upload_floor_plan(
    floor_id: UUID,
    file: UploadFile = File(...),
    width: int | None = Form(default=None),
    height: int | None = Form(default=None),
    scale: float = Form(default=0.05),
    _user: Any = Depends(OperatorOrAdmin),
    service: Any = Depends(get_floor_plan_service),
) -> dict[str, Any]:
    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file.")

    mime_type = file.content_type or ""
    filename = file.filename or ""
    if mime_type == "image/svg+xml" or filename.lower().endswith(".svg"):
        mime_type = "image/svg+xml"

    if width is None or height is None:
        if mime_type != "image/svg+xml":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="width and height form fields are required for non-SVG uploads.",
            )
        try:
            parsed_width, parsed_height = parse_svg_dimensions(image_bytes)
        except DomainValidationError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
        width = parsed_width if width is None else width
        height = parsed_height if height is None else height

    if scale <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="scale must be positive.")

    try:
        entity = service.upload(
            floor_id=floor_id,
            image_bytes=image_bytes,
            mime_type=mime_type,
            width=width,
            height=height,
            scale=scale,
        )
    except (LookupError, DomainValidationError, BusinessRuleViolation) as exc:
        raise _handle_domain_errors(exc)
    return success(data=_fp_dict(entity), message="FloorPlan uploaded.")


@router.delete("/floor-plans/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_floor_plan(
    entity_id: UUID,
    _user: Any = Depends(Administrator),
    service: Any = Depends(get_floor_plan_service),
) -> None:
    try:
        service.soft_delete(entity_id)
    except (LookupError, BusinessRuleViolation) as exc:
        raise _handle_domain_errors(exc)
