from dataclasses import dataclass
from uuid import UUID

from app.domain.entities.base import AuditableEntity
from app.domain.errors import DomainValidationError


@dataclass(kw_only=True)
class FloorPlan(AuditableEntity):
    floor_id: UUID
    image_path: str
    width: int
    height: int
    scale: float
    checksum: str
    mime_type: str
    version: int = 1
    is_active: bool = True

    def __post_init__(self) -> None:
        if self.width <= 0:
            raise DomainValidationError("FloorPlan width must be positive.")
        if self.height <= 0:
            raise DomainValidationError("FloorPlan height must be positive.")
        if self.scale <= 0:
            raise DomainValidationError("FloorPlan scale must be positive.")
        if not self.image_path.strip():
            raise DomainValidationError("FloorPlan image_path is required.")
        if not self.checksum.strip():
            raise DomainValidationError("FloorPlan checksum is required.")
        if not self.mime_type.strip():
            raise DomainValidationError("FloorPlan mime_type is required.")
