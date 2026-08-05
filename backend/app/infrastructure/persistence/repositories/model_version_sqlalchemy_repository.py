from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities.model_version import ModelVersion
from app.infrastructure.persistence.models import ModelVersionModel
from app.infrastructure.persistence.repositories.mappers import model_version_to_domain


class SqlAlchemyModelVersionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, entity: ModelVersion) -> ModelVersion:
        model = ModelVersionModel(
            id=str(entity.id),
            dataset_id=str(entity.dataset_id),
            floor_id=str(entity.floor_id),
            algorithm=entity.algorithm,
            model_version=entity.version,
            status=entity.status.value,
            hyperparameters=entity.hyperparameters,
            metrics=entity.metrics,
            training_time=entity.training_time,
            checksum=entity.checksum,
            published_at=entity.published_at,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            created_by=str(entity.created_by) if entity.created_by else None,
            updated_by=str(entity.updated_by) if entity.updated_by else None,
            is_active=entity.is_active,
        )
        self._session.add(model)
        self._session.flush()
        return model_version_to_domain(model)

    def get(self, entity_id: UUID) -> ModelVersion | None:
        model = self._session.get(ModelVersionModel, str(entity_id))
        return model_version_to_domain(model) if model else None

    def list_all(self) -> list[ModelVersion]:
        query = (
            select(ModelVersionModel)
            .where(ModelVersionModel.deleted_at.is_(None))
            .order_by(ModelVersionModel.created_at.desc())
        )
        return [model_version_to_domain(m) for m in self._session.scalars(query).all()]

    def list_by_floor(self, floor_id: UUID) -> list[ModelVersion]:
        query = (
            select(ModelVersionModel)
            .where(
                ModelVersionModel.floor_id == str(floor_id),
                ModelVersionModel.deleted_at.is_(None),
            )
            .order_by(ModelVersionModel.created_at.desc())
        )
        return [model_version_to_domain(m) for m in self._session.scalars(query).all()]

    def list_by_dataset(self, dataset_id: UUID) -> list[ModelVersion]:
        query = (
            select(ModelVersionModel)
            .where(
                ModelVersionModel.dataset_id == str(dataset_id),
                ModelVersionModel.deleted_at.is_(None),
            )
            .order_by(ModelVersionModel.created_at.desc())
        )
        return [model_version_to_domain(m) for m in self._session.scalars(query).all()]

    def has_published_on_floor(self, floor_id: UUID) -> bool:
        query = select(ModelVersionModel.id).where(
            ModelVersionModel.floor_id == str(floor_id),
            ModelVersionModel.status == "Published",
            ModelVersionModel.deleted_at.is_(None),
        ).limit(1)
        return self._session.scalar(query) is not None

    def get_published_on_floor(self, floor_id: UUID) -> ModelVersion | None:
        query = select(ModelVersionModel).where(
            ModelVersionModel.floor_id == str(floor_id),
            ModelVersionModel.status == "Published",
            ModelVersionModel.deleted_at.is_(None),
        ).limit(1)
        model = self._session.scalar(query)
        return model_version_to_domain(model) if model else None

    def update(self, entity: ModelVersion) -> ModelVersion:
        model = self._session.get(ModelVersionModel, str(entity.id))
        if model is None:
            raise LookupError("ModelVersion not found.")
        model.algorithm = entity.algorithm
        model.model_version = entity.version
        model.status = entity.status.value
        model.hyperparameters = entity.hyperparameters
        model.metrics = entity.metrics
        model.training_time = entity.training_time
        model.checksum = entity.checksum
        model.published_at = entity.published_at
        model.updated_at = entity.updated_at
        model.updated_by = str(entity.updated_by) if entity.updated_by else None
        model.is_active = entity.is_active
        model.deleted_at = entity.deleted_at
        self._session.flush()
        return model_version_to_domain(model)

    def soft_delete(self, entity_id: UUID, deleted_by: UUID | None = None) -> None:
        model = self._session.get(ModelVersionModel, str(entity_id))
        if model is None:
            raise LookupError("ModelVersion not found.")
        entity = model_version_to_domain(model)
        entity.soft_delete(deleted_by)
        self.update(entity)
