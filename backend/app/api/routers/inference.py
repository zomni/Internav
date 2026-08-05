import time
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.application.inference_service import ObservationInput
from app.domain.entities.user import UserRole
from app.domain.errors import BusinessRuleViolation, DomainValidationError
from app.domain.events import DomainEvent, EventBus, EventType

from ..dependencies import get_inference_service, require_roles
from ..responses import success

router = APIRouter(tags=["inference"])

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


@router.post("/inference")
def estimate_position(
    body: dict[str, Any],
    _user: Any = Depends(OperatorOrAdmin),
    service: Any = Depends(get_inference_service),
) -> dict[str, Any]:
    start = time.perf_counter()
    try:
        floor_id = UUID(body["floor_id"])
        observations = [
            ObservationInput(
                bssid=obs["bssid"],
                ssid=obs["ssid"],
                rssi=obs["rssi"],
                frequency=obs["frequency"],
            )
            for obs in body["observations"]
        ]
        result = service.estimate_position(floor_id, observations)
    except (LookupError, BusinessRuleViolation, DomainValidationError) as exc:
        raise _handle_domain_errors(exc)
    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
    result.inference_time_ms = elapsed_ms
    EventBus.publish(DomainEvent(EventType.INFERENCE_EXECUTED, UUID(result.model_version_id), {
        "floor_id": str(floor_id),
        "predicted_cell_id": result.predicted_cell_id,
        "confidence": result.confidence,
    }))
    return success(
        data={
            "predicted_cell_id": result.predicted_cell_id,
            "center_x": result.center_x,
            "center_y": result.center_y,
            "confidence": result.confidence,
            "candidate_cells": [
                {
                    "cell_id": c.cell_id,
                    "center_x": c.center_x,
                    "center_y": c.center_y,
                    "score": c.score,
                }
                for c in result.candidate_cells
            ],
            "model_version_id": result.model_version_id,
            "inference_time_ms": result.inference_time_ms,
        }
    )
