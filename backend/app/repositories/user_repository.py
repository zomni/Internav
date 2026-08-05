from typing import Protocol

from app.domain.entities.user import User, UserRole
from app.repositories.base import Repository


class UserRepository(Repository[User], Protocol):
    def list_all(self) -> list[User]: ...

    def get_by_email(self, email: str) -> User | None: ...

    def has_role(self, role: UserRole) -> bool: ...
