from dataclasses import dataclass
from uuid import UUID

from app.domain.entities.base import AuditableEntity
from app.domain.errors import DomainValidationError


@dataclass(kw_only=True)
class Building(AuditableEntity):
    site_id: UUID
    name: str
    code: str
    description: str | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise DomainValidationError("Building name is required.")
        if not self.code.strip():
            raise DomainValidationError("Building code is required.")
