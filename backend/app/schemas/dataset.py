from uuid import UUID

from pydantic import BaseModel


class DatasetCreateRequest(BaseModel):
    name: str


class DatasetAddCampaignsRequest(BaseModel):
    campaign_ids: list[UUID]


class DatasetResponse(BaseModel):
    id: UUID
    name: str
    status: str
    fingerprint_count: int
    observation_count: int
    floor_count: int
    dataset_version: int
    version: int
    is_active: bool
    created_at: str
    updated_at: str


class DatasetCampaignResponse(BaseModel):
    id: UUID
    dataset_id: UUID
    campaign_id: UUID
    created_at: str
