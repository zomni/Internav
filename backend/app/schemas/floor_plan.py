from uuid import UUID

from pydantic import BaseModel, Field


class FloorPlanResponse(BaseModel):
    id: UUID
    floor_id: UUID
    image_path: str
    width: int
    height: int
    scale: float
    checksum: str
    mime_type: str
    version: int
    is_active: bool
    created_at: str
    updated_at: str


class GridResponse(BaseModel):
    id: UUID
    floor_id: UUID
    name: str
    cell_size: int
    status: str
    version: int
    is_active: bool
    created_at: str
    updated_at: str


class CellResponse(BaseModel):
    id: UUID
    grid_id: UUID
    row: int
    column: int
    center_x: float
    center_y: float
    walkable: bool
    version: int
    is_active: bool
    created_at: str
    updated_at: str


class GridGenerateRequest(BaseModel):
    floor_id: UUID
    name: str
    cell_size: int = Field(gt=0)
