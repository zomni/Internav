from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities.user import User, UserRole
from app.infrastructure.persistence.models import UserModel
from app.infrastructure.persistence.repositories.mappers import user_to_domain


class SqlAlchemyUserRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, entity: User) -> User:
        model = UserModel(
            id=str(entity.id),
            email=entity.email.lower(),
            password_hash=entity.password_hash,
            role=entity.role.value,
            organization_id=str(entity.organization_id) if entity.organization_id else None,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            created_by=str(entity.created_by) if entity.created_by else None,
            updated_by=str(entity.updated_by) if entity.updated_by else None,
            version=entity.version,
            is_active=entity.is_active,
        )
        self._session.add(model)
        self._session.flush()
        return user_to_domain(model)

    def get(self, entity_id: UUID) -> User | None:
        model = self._session.get(UserModel, str(entity_id))
        return user_to_domain(model) if model else None

    def list_all(self) -> list[User]:
        query = (
            select(UserModel)
            .where(UserModel.deleted_at.is_(None))
            .order_by(UserModel.created_at.desc())
        )
        return [user_to_domain(m) for m in self._session.scalars(query).all()]

    def get_by_email(self, email: str) -> User | None:
        model = self._session.scalar(select(UserModel).where(UserModel.email == email.lower()))
        return user_to_domain(model) if model else None

    def has_role(self, role: UserRole) -> bool:
        return (
            self._session.scalar(select(UserModel.id).where(UserModel.role == role.value))
            is not None
        )

    def update(self, entity: User) -> User:
        model = self._session.get(UserModel, str(entity.id))
        if model is None:
            raise LookupError("User not found.")
        model.email = entity.email.lower()
        model.password_hash = entity.password_hash
        model.role = entity.role.value
        model.organization_id = str(entity.organization_id) if entity.organization_id else None
        model.updated_at = entity.updated_at
        model.updated_by = str(entity.updated_by) if entity.updated_by else None
        model.version = entity.version
        model.is_active = entity.is_active
        model.deleted_at = entity.deleted_at
        self._session.flush()
        return user_to_domain(model)

    def soft_delete(self, entity_id: UUID, deleted_by: UUID | None = None) -> None:
        model = self._session.get(UserModel, str(entity_id))
        if model is None:
            raise LookupError("User not found.")
        entity = user_to_domain(model)
        entity.soft_delete(deleted_by)
        self.update(entity)
