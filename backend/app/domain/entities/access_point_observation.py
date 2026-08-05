from dataclasses import dataclass
from uuid import UUID

from app.domain.entities.base import AuditableEntity
from app.domain.errors import DomainValidationError


@dataclass(kw_only=True)
class AccessPointObservation(AuditableEntity):
    fingerprint_id: UUID
    bssid: str
    ssid: str
    rssi: int
    frequency: int
    channel: int = 0
    band: str = ""
    security: str = ""

    def __post_init__(self) -> None:
        if not self.bssid.strip():
            raise DomainValidationError("AccessPointObservation bssid is required.")
        if self.rssi < -100 or self.rssi > 0:
            raise DomainValidationError("AccessPointObservation rssi must be between -100 and 0.")
        if self.frequency <= 0:
            raise DomainValidationError("AccessPointObservation frequency must be positive.")
