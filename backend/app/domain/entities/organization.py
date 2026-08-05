from dataclasses import dataclass

from app.domain.entities.base import AuditableEntity
from app.domain.errors import DomainValidationError


@dataclass(kw_only=True)
class Organization(AuditableEntity):
    name: str
    code: str
    description: str | None = None

    def __post_init__(self) -> None:
        if not 3 <= len(self.name.strip()) <= 120:
            raise DomainValidationError("Organization name length must be between 3 and 120.")
        if not self.code or self.code != self.code.upper():
            raise DomainValidationError("Organization code is required and must be uppercase.")
