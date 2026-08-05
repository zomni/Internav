from uuid import UUID

from pydantic import BaseModel


class ModelVersionCreateRequest(BaseModel):
    dataset_id: UUID
    floor_id: UUID
    algorithm: str
    hyperparameters: str | None = None


class ModelVersionReadyRequest(BaseModel):
    metrics: str | None = None
    training_time: float | None = None
    checksum: str | None = None


class ModelVersionResponse(BaseModel):
    id: UUID
    dataset_id: UUID
    floor_id: UUID
    algorithm: str
    version: int
    status: str
    hyperparameters: str | None
    metrics: str | None
    training_time: float | None
    checksum: str | None
    published_at: str | None
    version_num: int
    is_active: bool
    created_at: str
    updated_at: str
