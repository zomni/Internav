from dataclasses import dataclass
from uuid import UUID

from app.domain.entities.base import AuditableEntity
from app.domain.errors import DomainValidationError


@dataclass(kw_only=True)
class Cell(AuditableEntity):
    grid_id: UUID
    row: int
    column: int
    center_x: float
    center_y: float
    walkable: bool = True

    def __post_init__(self) -> None:
        if isinstance(self.row, bool) or not isinstance(self.row, int):
            raise DomainValidationError("Cell row must be an integer.")
        if isinstance(self.column, bool) or not isinstance(self.column, int):
            raise DomainValidationError("Cell column must be an integer.")
        if self.row < 0:
            raise DomainValidationError("Cell row must be non-negative.")
        if self.column < 0:
            raise DomainValidationError("Cell column must be non-negative.")
        if self.center_x < 0:
            raise DomainValidationError("Cell center_x must be non-negative.")
        if self.center_y < 0:
            raise DomainValidationError("Cell center_y must be non-negative.")
