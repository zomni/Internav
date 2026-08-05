from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from app.domain.entities.base import AuditableEntity
from app.domain.errors import DomainValidationError


class GridStatus(StrEnum):
    DRAFT = "Draft"
    ACTIVE = "Active"
    LOCKED = "Locked"


@dataclass(kw_only=True)
class Grid(AuditableEntity):
    floor_id: UUID
    name: str
    cell_size: int
    status: GridStatus = GridStatus.DRAFT

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise DomainValidationError("Grid name is required.")
        if isinstance(self.cell_size, bool) or not isinstance(self.cell_size, int):
            raise DomainValidationError("Grid cell_size must be an integer.")
        if self.cell_size <= 0:
            raise DomainValidationError("Grid cell_size must be positive.")
