from uuid import UUID

from app.domain.entities.user import User, UserRole
from app.domain.errors import BusinessRuleViolation
from app.repositories.user_repository import UserRepository
from app.security.passwords import hash_password


class UserService:
    def __init__(self, user_repository: UserRepository) -> None:
        self._user_repo = user_repository

    def list_all(self) -> list[User]:
        return self._user_repo.list_all()

    def get(self, user_id: UUID) -> User:
        user = self._user_repo.get(user_id)
        if user is None:
            raise LookupError("User not found.")
        return user

    def create(
        self,
        email: str,
        password: str,
        role: UserRole,
        organization_id: UUID | None = None,
    ) -> User:
        existing = self._user_repo.get_by_email(email)
        if existing is not None:
            raise BusinessRuleViolation(f"A user with email '{email}' already exists.")

        user = User(
            email=email,
            password_hash=hash_password(password),
            role=role,
            organization_id=organization_id,
        )
        return self._user_repo.add(user)

    def update_role(self, user_id: UUID, role: UserRole) -> User:
        user = self.get(user_id)
        user.touch()
        user.role = role
        return self._user_repo.update(user)

    def update_password(self, user_id: UUID, new_password: str) -> User:
        user = self.get(user_id)
        user.touch()
        user.password_hash = hash_password(new_password)
        return self._user_repo.update(user)

    def deactivate(self, user_id: UUID) -> User:
        user = self.get(user_id)
        user.touch()
        user.is_active = False
        return self._user_repo.update(user)

    def activate(self, user_id: UUID) -> User:
        user = self.get(user_id)
        user.touch()
        user.is_active = True
        return self._user_repo.update(user)

    def soft_delete(self, user_id: UUID) -> None:
        user = self.get(user_id)
        if user.role == UserRole.ADMINISTRATOR:
            raise BusinessRuleViolation("Cannot delete an Administrator user.")
        self._user_repo.soft_delete(user_id)
