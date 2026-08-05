from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from app.domain.entities.base import AuditableEntity
from app.domain.errors import BusinessRuleViolation, DomainValidationError


@dataclass(kw_only=True)
class Fingerprint(AuditableEntity):
    campaign_id: UUID
    cell_id: UUID
    device_id: str
    captured_at: datetime
    sample_number: int
    orientation: float = 0.0
    notes: str | None = None
    observation_count: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        if not self.device_id.strip():
            raise DomainValidationError("Fingerprint device_id is required.")

    def ensure_immutable(self) -> None:
        if self.version > 1:
            raise BusinessRuleViolation("Fingerprint is immutable after creation.")
