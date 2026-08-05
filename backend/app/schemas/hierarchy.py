from uuid import UUID

from pydantic import BaseModel, Field


class OrganizationCreateRequest(BaseModel):
    name: str
    code: str
    description: str | None = None


class OrganizationUpdateRequest(BaseModel):
    name: str | None = None
    code: str | None = None
    description: str | None = None


class SiteCreateRequest(BaseModel):
    organization_id: UUID
    name: str
    code: str
    timezone: str
    address: str | None = None
    metadata: str | None = None


class SiteUpdateRequest(BaseModel):
    name: str | None = None
    code: str | None = None
    timezone: str | None = None
    address: str | None = None
    metadata: str | None = None


class BuildingCreateRequest(BaseModel):
    site_id: UUID
    name: str
    code: str
    description: str | None = None


class BuildingUpdateRequest(BaseModel):
    name: str | None = None
    code: str | None = None
    description: str | None = None


class FloorCreateRequest(BaseModel):
    building_id: UUID
    name: str
    level: int
    display_order: int


class FloorUpdateRequest(BaseModel):
    name: str | None = None
    level: int | None = None
    display_order: int | None = None


class PageQuery(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
