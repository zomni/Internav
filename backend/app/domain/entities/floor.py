from dataclasses import dataclass
from uuid import UUID

from app.domain.entities.base import AuditableEntity
from app.domain.errors import DomainValidationError


@dataclass(kw_only=True)
class Floor(AuditableEntity):
    building_id: UUID
    name: str
    level: int
    display_order: int

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise DomainValidationError("Floor name is required.")
        if isinstance(self.level, bool) or not isinstance(self.level, int):
            raise DomainValidationError("Floor level must be an integer.")
