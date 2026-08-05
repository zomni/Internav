from dataclasses import dataclass
from uuid import UUID

from app.domain.entities.base import AuditableEntity
from app.domain.errors import DomainValidationError


@dataclass(kw_only=True)
class Site(AuditableEntity):
    organization_id: UUID
    name: str
    code: str
    timezone: str
    address: str | None = None
    metadata: str | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise DomainValidationError("Site name is required.")
        if not self.code.strip():
            raise DomainValidationError("Site code is required.")
        if not self.timezone.strip():
            raise DomainValidationError("Site timezone is required.")
