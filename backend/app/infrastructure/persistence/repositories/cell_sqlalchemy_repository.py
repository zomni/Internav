from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities.cell import Cell
from app.infrastructure.persistence.models import CellModel
from app.infrastructure.persistence.repositories.mappers import cell_to_domain


class SqlAlchemyCellRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, entity: Cell) -> Cell:
        model = CellModel(
            id=str(entity.id),
            grid_id=str(entity.grid_id),
            row=entity.row,
            column=entity.column,
            center_x=entity.center_x,
            center_y=entity.center_y,
            walkable=entity.walkable,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            created_by=str(entity.created_by) if entity.created_by else None,
            updated_by=str(entity.updated_by) if entity.updated_by else None,
            version=entity.version,
            is_active=entity.is_active,
        )
        self._session.add(model)
        self._session.flush()
        return cell_to_domain(model)

    def get(self, entity_id: UUID) -> Cell | None:
        model = self._session.get(CellModel, str(entity_id))
        return cell_to_domain(model) if model else None

    def list_by_grid(self, grid_id: UUID) -> list[Cell]:
        query = (
            select(CellModel)
            .where(CellModel.grid_id == str(grid_id))
            .order_by(CellModel.row, CellModel.column)
        )
        return [cell_to_domain(m) for m in self._session.scalars(query).all()]

    def has_by_row_column(self, grid_id: UUID, row: int, column: int) -> bool:
        return (
            self._session.scalar(
                select(CellModel.id).where(
                    CellModel.grid_id == str(grid_id),
                    CellModel.row == row,
                    CellModel.column == column,
                    CellModel.deleted_at.is_(None),
                )
            )
            is not None
        )

    def delete_by_grid(self, grid_id: UUID) -> None:
        from sqlalchemy import delete

        self._session.execute(delete(CellModel).where(CellModel.grid_id == str(grid_id)))

    def update(self, entity: Cell) -> Cell:
        model = self._session.get(CellModel, str(entity.id))
        if model is None:
            raise LookupError("Cell not found.")
        model.row = entity.row
        model.column = entity.column
        model.center_x = entity.center_x
        model.center_y = entity.center_y
        model.walkable = entity.walkable
        model.updated_at = entity.updated_at
        model.updated_by = str(entity.updated_by) if entity.updated_by else None
        model.version = entity.version
        model.is_active = entity.is_active
        model.deleted_at = entity.deleted_at
        self._session.flush()
        return cell_to_domain(model)

    def soft_delete(self, entity_id: UUID, deleted_by: UUID | None = None) -> None:
        model = self._session.get(CellModel, str(entity_id))
        if model is None:
            raise LookupError("Cell not found.")
        entity = cell_to_domain(model)
        entity.soft_delete(deleted_by)
        self.update(entity)
