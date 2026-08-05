from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities.grid import Grid, GridStatus
from app.infrastructure.persistence.models import GridModel
from app.infrastructure.persistence.repositories.mappers import grid_to_domain


class SqlAlchemyGridRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, entity: Grid) -> Grid:
        model = GridModel(
            id=str(entity.id),
            floor_id=str(entity.floor_id),
            name=entity.name,
            cell_size=entity.cell_size,
            status=entity.status.value,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            created_by=str(entity.created_by) if entity.created_by else None,
            updated_by=str(entity.updated_by) if entity.updated_by else None,
            version=entity.version,
            is_active=entity.is_active,
        )
        self._session.add(model)
        self._session.flush()
        return grid_to_domain(model)

    def get(self, entity_id: UUID) -> Grid | None:
        model = self._session.get(GridModel, str(entity_id))
        return grid_to_domain(model) if model else None

    def list_all(self) -> list[Grid]:
        query = (
            select(GridModel)
            .where(GridModel.deleted_at.is_(None))
            .order_by(GridModel.created_at.desc())
        )
        return [grid_to_domain(m) for m in self._session.scalars(query).all()]

    def list_by_floor(self, floor_id: UUID) -> list[Grid]:
        query = (
            select(GridModel)
            .where(
                GridModel.floor_id == str(floor_id),
                GridModel.deleted_at.is_(None),
            )
            .order_by(GridModel.created_at.desc())
        )
        return [grid_to_domain(m) for m in self._session.scalars(query).all()]

    def get_active(self, floor_id: UUID) -> Grid | None:
        model = self._session.scalar(
            select(GridModel).where(
                GridModel.floor_id == str(floor_id),
                GridModel.status == GridStatus.ACTIVE.value,
                GridModel.deleted_at.is_(None),
            )
        )
        return grid_to_domain(model) if model else None

    def has_active(self, floor_id: UUID) -> bool:
        return (
            self._session.scalar(
                select(GridModel.id).where(
                    GridModel.floor_id == str(floor_id),
                    GridModel.status == GridStatus.ACTIVE.value,
                    GridModel.deleted_at.is_(None),
                )
            )
            is not None
        )

    def update(self, entity: Grid) -> Grid:
        model = self._session.get(GridModel, str(entity.id))
        if model is None:
            raise LookupError("Grid not found.")
        model.name = entity.name
        model.cell_size = entity.cell_size
        model.status = entity.status.value
        model.updated_at = entity.updated_at
        model.updated_by = str(entity.updated_by) if entity.updated_by else None
        model.version = entity.version
        model.is_active = entity.is_active
        model.deleted_at = entity.deleted_at
        self._session.flush()
        return grid_to_domain(model)

    def soft_delete(self, entity_id: UUID, deleted_by: UUID | None = None) -> None:
        model = self._session.get(GridModel, str(entity_id))
        if model is None:
            raise LookupError("Grid not found.")
        entity = grid_to_domain(model)
        entity.soft_delete(deleted_by)
        self.update(entity)
