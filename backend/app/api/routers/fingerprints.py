from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.domain.entities.user import UserRole
from app.domain.errors import BusinessRuleViolation, DomainValidationError

from ..dependencies import get_fingerprint_service, require_roles
from ..responses import success

router = APIRouter(tags=["fingerprints"])

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


def _obs_dict(o: Any) -> dict[str, Any]:
    return {
        "id": str(o.id),
        "fingerprint_id": str(o.fingerprint_id),
        "bssid": o.bssid,
        "ssid": o.ssid,
        "rssi": o.rssi,
        "frequency": o.frequency,
        "channel": o.channel,
        "band": o.band,
        "security": o.security,
        "version": o.version,
        "is_active": o.is_active,
        "created_at": o.created_at.isoformat(),
        "updated_at": o.updated_at.isoformat(),
    }


def _fp_dict(fp: Any, observations: list[Any] | None = None) -> dict[str, Any]:
    return {
        "id": str(fp.id),
        "campaign_id": str(fp.campaign_id),
        "cell_id": str(fp.cell_id),
        "device_id": fp.device_id,
        "captured_at": fp.captured_at.isoformat(),
        "sample_number": fp.sample_number,
        "orientation": fp.orientation,
        "notes": fp.notes,
        "version": fp.version,
        "is_active": fp.is_active,
        "created_at": fp.created_at.isoformat(),
        "updated_at": fp.updated_at.isoformat(),
        "observations": [_obs_dict(o) for o in observations] if observations else [],
    }


@router.get("/campaigns/{campaign_id}/fingerprints")
def list_fingerprints(
    campaign_id: UUID,
    service: Any = Depends(get_fingerprint_service),
) -> dict[str, Any]:
    try:
        items = service.list_by_campaign(campaign_id)
    except LookupError as exc:
        raise _handle_domain_errors(exc)
    return success(data=[_fp_dict(fp) for fp in items])


@router.get("/fingerprints/{fingerprint_id}")
def get_fingerprint(
    fingerprint_id: UUID,
    service: Any = Depends(get_fingerprint_service),
) -> dict[str, Any]:
    try:
        entity = service.get(fingerprint_id)
    except LookupError as exc:
        raise _handle_domain_errors(exc)
    observations = service.get_observations(fingerprint_id)
    return success(data=_fp_dict(entity, observations))


@router.post(
    "/campaigns/{campaign_id}/fingerprints",
    status_code=status.HTTP_201_CREATED,
)
def create_fingerprint(
    campaign_id: UUID,
    body: dict[str, Any],
    _user: Any = Depends(OperatorOrAdmin),
    service: Any = Depends(get_fingerprint_service),
) -> dict[str, Any]:
    try:
        from datetime import datetime

        captured_at_str = body["captured_at"]
        captured_at = datetime.fromisoformat(captured_at_str)
        observations = body.get("observations", [])

        entity = service.create(
            campaign_id=campaign_id,
            cell_id=UUID(body["cell_id"]),
            device_id=body["device_id"],
            captured_at=captured_at,
            sample_number=body["sample_number"],
            orientation=body.get("orientation", 0.0),
            notes=body.get("notes"),
            observations=observations,
        )
    except (LookupError, DomainValidationError, BusinessRuleViolation) as exc:
        raise _handle_domain_errors(exc)
    observations = service.get_observations(entity.id)
    return success(data=_fp_dict(entity, observations), message="Fingerprint created.")
