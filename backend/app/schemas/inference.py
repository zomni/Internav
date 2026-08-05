from pydantic import BaseModel


class InferenceObservationRequest(BaseModel):
    bssid: str
    ssid: str
    rssi: int
    frequency: int


class InferenceRequest(BaseModel):
    floor_id: str
    observations: list[InferenceObservationRequest]


class CandidateCellResponse(BaseModel):
    cell_id: str
    center_x: float
    center_y: float
    score: float


class InferenceResponse(BaseModel):
    predicted_cell_id: str
    center_x: float
    center_y: float
    confidence: float
    candidate_cells: list[CandidateCellResponse]
    model_version_id: str
    inference_time_ms: float
