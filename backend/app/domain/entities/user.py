from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from app.domain.entities.base import AuditableEntity
from app.domain.errors import DomainValidationError


class UserRole(StrEnum):
    ADMINISTRATOR = "Administrator"
    OPERATOR = "Operator"
    VIEWER = "Viewer"


@dataclass(kw_only=True)
class User(AuditableEntity):
    email: str
    password_hash: str
    role: UserRole
    organization_id: UUID | None = None

    def __post_init__(self) -> None:
        if "@" not in self.email or not self.email.strip():
            raise DomainValidationError("User email is required.")
        if not self.password_hash:
            raise DomainValidationError("User password hash is required.")
