from uuid import UUID

from pydantic import BaseModel


class CampaignCreateRequest(BaseModel):
    name: str


class CampaignResponse(BaseModel):
    id: UUID
    floor_id: UUID
    name: str
    status: str
    started_at: str | None = None
    finished_at: str | None = None
    version: int
    is_active: bool
    created_at: str
    updated_at: str


class FingerprintObservationCreateRequest(BaseModel):
    bssid: str
    ssid: str = ""
    rssi: int
    frequency: int
    channel: int = 0
    band: str = ""
    security: str = ""


class FingerprintCreateRequest(BaseModel):
    cell_id: UUID
    device_id: str
    captured_at: str
    sample_number: int
    orientation: float = 0.0
    notes: str | None = None
    observations: list[FingerprintObservationCreateRequest] = []


class AccessPointObservationResponse(BaseModel):
    id: UUID
    fingerprint_id: UUID
    bssid: str
    ssid: str
    rssi: int
    frequency: int
    channel: int
    band: str
    security: str
    version: int
    is_active: bool
    created_at: str
    updated_at: str


class FingerprintResponse(BaseModel):
    id: UUID
    campaign_id: UUID
    cell_id: UUID
    device_id: str
    captured_at: str
    sample_number: int
    orientation: float
    notes: str | None = None
    version: int
    is_active: bool
    created_at: str
    updated_at: str
    observations: list[AccessPointObservationResponse] = []
