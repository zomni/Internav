import hashlib
import json
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import FileResponse, JSONResponse

from app.domain.entities.model_version import ModelVersionStatus
from app.domain.entities.user import UserRole
from app.domain.errors import BusinessRuleViolation, DomainValidationError
from app.domain.events import DomainEvent, EventBus, EventType

from ..dependencies import get_model_update_service, get_model_version_service, require_roles
from ..responses import success

router = APIRouter(tags=["models"])

Administrator = require_roles(UserRole.ADMINISTRATOR)
OperatorOrAdmin = require_roles(UserRole.ADMINISTRATOR, UserRole.OPERATOR)


def _handle_domain_errors(exc: Exception) -> HTTPException:
    if isinstance(exc, LookupError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, BusinessRuleViolation):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if isinstance(exc, DomainValidationError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    if isinstance(exc, ValueError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal error."
    )


def _model_dict(m: Any) -> dict[str, Any]:
    return {
        "id": str(m.id),
        "dataset_id": str(m.dataset_id),
        "floor_id": str(m.floor_id),
        "algorithm": m.algorithm,
        "version": m.version,
        "status": m.status.value if hasattr(m.status, "value") else m.status,
        "hyperparameters": m.hyperparameters,
        "metrics": m.metrics,
        "training_time": m.training_time,
        "checksum": m.checksum,
        "published_at": m.published_at.isoformat() if m.published_at else None,
        "version_num": m.version,
        "is_active": m.is_active,
        "created_at": m.created_at.isoformat(),
        "updated_at": m.updated_at.isoformat(),
    }


@router.get("/models")
def list_models(
    service: Any = Depends(get_model_version_service),
) -> dict[str, Any]:
    items = service.list_all()
    return success(data=[_model_dict(m) for m in items])


@router.get("/models/{model_id}")
def get_model(
    model_id: UUID,
    service: Any = Depends(get_model_version_service),
) -> dict[str, Any]:
    try:
        entity = service.get(model_id)
    except LookupError as exc:
        raise _handle_domain_errors(exc)
    return success(data=_model_dict(entity))


@router.get("/floors/{floor_id}/models")
def list_models_by_floor(
    floor_id: UUID,
    service: Any = Depends(get_model_version_service),
) -> dict[str, Any]:
    try:
        items = service.list_by_floor(floor_id)
    except LookupError as exc:
        raise _handle_domain_errors(exc)
    return success(data=[_model_dict(m) for m in items])


@router.post(
    "/models",
    status_code=status.HTTP_201_CREATED,
)
def create_model(
    body: dict[str, Any],
    _user: Any = Depends(OperatorOrAdmin),
    service: Any = Depends(get_model_version_service),
) -> dict[str, Any]:
    try:
        entity = service.create(
            dataset_id=UUID(body["dataset_id"]),
            floor_id=UUID(body["floor_id"]),
            algorithm=body["algorithm"],
            hyperparameters=body.get("hyperparameters"),
        )
    except (LookupError, DomainValidationError) as exc:
        raise _handle_domain_errors(exc)
    return success(data=_model_dict(entity), message="ModelVersion created.")


@router.patch("/models/{model_id}/mark-ready")
def mark_ready(
    model_id: UUID,
    body: dict[str, Any] | None = None,
    _user: Any = Depends(OperatorOrAdmin),
    service: Any = Depends(get_model_version_service),
) -> dict[str, Any]:
    try:
        entity = service.mark_ready(
            model_version_id=model_id,
            metrics=body.get("metrics") if body else None,
            training_time=body.get("training_time") if body else None,
            checksum=body.get("checksum") if body else None,
        )
    except (LookupError, BusinessRuleViolation) as exc:
        raise _handle_domain_errors(exc)
    return success(data=_model_dict(entity))


@router.patch("/models/{model_id}/mark-failed")
def mark_failed(
    model_id: UUID,
    _user: Any = Depends(OperatorOrAdmin),
    service: Any = Depends(get_model_version_service),
) -> dict[str, Any]:
    try:
        entity = service.mark_failed(model_version_id=model_id)
    except (LookupError, BusinessRuleViolation) as exc:
        raise _handle_domain_errors(exc)
    return success(data=_model_dict(entity))


@router.patch("/models/{model_id}/publish")
def publish(
    model_id: UUID,
    _user: Any = Depends(OperatorOrAdmin),
    service: Any = Depends(get_model_version_service),
) -> dict[str, Any]:
    try:
        entity = service.publish(model_version_id=model_id)
    except (LookupError, BusinessRuleViolation) as exc:
        raise _handle_domain_errors(exc)
    return success(data=_model_dict(entity))


@router.patch("/models/{model_id}/unpublish")
def unpublish(
    model_id: UUID,
    _user: Any = Depends(Administrator),
    service: Any = Depends(get_model_version_service),
) -> dict[str, Any]:
    try:
        entity = service.unpublish(model_version_id=model_id)
    except (LookupError, BusinessRuleViolation) as exc:
        raise _handle_domain_errors(exc)
    return success(data=_model_dict(entity))


@router.patch("/models/{model_id}/archive")
def archive(
    model_id: UUID,
    _user: Any = Depends(OperatorOrAdmin),
    service: Any = Depends(get_model_version_service),
) -> dict[str, Any]:
    try:
        entity = service.archive(model_version_id=model_id)
    except (LookupError, BusinessRuleViolation) as exc:
        raise _handle_domain_errors(exc)
    return success(data=_model_dict(entity))


@router.delete("/models/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_model(
    model_id: UUID,
    _user: Any = Depends(Administrator),
    service: Any = Depends(get_model_version_service),
) -> None:
    try:
        service.soft_delete(model_version_id=model_id)
    except (LookupError, BusinessRuleViolation) as exc:
        raise _handle_domain_errors(exc)


@router.post(
    "/models/{model_id}/train",
    status_code=status.HTTP_200_OK,
)
def train_model(
    model_id: UUID,
    _user: Any = Depends(OperatorOrAdmin),
    service: Any = Depends(get_model_version_service),
) -> dict[str, Any]:
    try:
        entity = service.train(model_version_id=model_id)
    except (LookupError, ValueError, RuntimeError, BusinessRuleViolation) as exc:
        raise _handle_domain_errors(exc)
    if entity.status == ModelVersionStatus.FAILED:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "detail": (
                    "Training failed. Ensure the dataset is built and contains "
                    "completed campaigns with fingerprints."
                )
            },
        )
    return success(data=_model_dict(entity), message="Training completed.")


@router.get("/floors/{floor_id}/model-update")
def check_model_update(
    floor_id: UUID,
    _user: Any = Depends(OperatorOrAdmin),
    service: Any = Depends(get_model_update_service),
) -> dict[str, Any]:
    try:
        result = service.check_for_update(floor_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return success(data=result)


@router.get("/models/{model_id}/download")
def download_model(
    model_id: UUID,
    request: Request,
    _user: Any = Depends(OperatorOrAdmin),
) -> FileResponse:
    service = request.app.state.model_version_service
    try:
        paths = service.get_artifact_paths(model_id)
    except (LookupError, BusinessRuleViolation, RuntimeError) as exc:
        if isinstance(exc, LookupError):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
        if isinstance(exc, BusinessRuleViolation):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
    EventBus.publish(DomainEvent(EventType.MODEL_DOWNLOADED, model_id))
    return FileResponse(
        paths["model_path"], media_type="application/octet-stream", filename=f"{model_id}.bin"
    )


@router.get("/models/{model_id}/mobile-bundle")
def download_mobile_bundle(
    model_id: UUID,
    request: Request,
    _user: Any = Depends(OperatorOrAdmin),
) -> Response:
    """Serve a JSON bundle (feature schema + reference vectors) for offline inference on Android.

    The ``X-Model-Checksum`` header contains the SHA-256 of the exact body bytes,
    which clients use to validate the download.
    """
    service = request.app.state.model_version_service
    try:
        bundle = service.get_mobile_bundle(model_id)
    except (LookupError, BusinessRuleViolation, RuntimeError) as exc:
        if isinstance(exc, LookupError):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
        if isinstance(exc, BusinessRuleViolation):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

    body = json.dumps(bundle, separators=(",", ":"), ensure_ascii=False)
    checksum = hashlib.sha256(body.encode("utf-8")).hexdigest()
    return Response(
        content=body.encode("utf-8"),
        media_type="application/json",
        headers={"X-Model-Checksum": checksum, "Cache-Control": "no-store"},
    )
