import logging
import time
from dataclasses import dataclass, field
from uuid import UUID

logger = logging.getLogger("app.inference")

from app.domain.errors import DomainValidationError
from app.repositories.access_point_observation_repository import AccessPointObservationRepository
from app.repositories.cell_repository import CellRepository
from app.repositories.fingerprint_repository import FingerprintRepository
from app.repositories.model_version_repository import ModelVersionRepository


@dataclass
class ObservationInput:
    bssid: str
    ssid: str
    rssi: int
    frequency: int


@dataclass
class CandidateCell:
    cell_id: str
    center_x: float
    center_y: float
    score: float


@dataclass
class InferenceResult:
    predicted_cell_id: str
    center_x: float
    center_y: float
    confidence: float
    candidate_cells: list[CandidateCell] = field(default_factory=list)
    model_version_id: str = ""
    inference_time_ms: float = 0.0


class InferenceService:
    def __init__(
        self,
        model_version_repository: ModelVersionRepository,
        fingerprint_repository: FingerprintRepository,
        cell_repository: CellRepository,
        observation_repository: AccessPointObservationRepository,
    ) -> None:
        self._model_version_repo = model_version_repository
        self._fingerprint_repo = fingerprint_repository
        self._cell_repo = cell_repository
        self._obs_repo = observation_repository

    def estimate_position(
        self,
        floor_id: UUID,
        observations: list[ObservationInput],
    ) -> InferenceResult:
        start = time.perf_counter()
        if not observations:
            raise DomainValidationError("At least one observation is required.")

        model = self._model_version_repo.get_published_on_floor(floor_id)
        if model is None:
            logger.warning("No published model found for floor %s", floor_id)
            raise LookupError("No published model found for this floor.")

        cell_scores: dict[str, float] = {}

        fingerprints = self._fingerprint_repo.list_by_floor(floor_id)
        for fp in fingerprints:
            score = self._compute_similarity(observations, fp.id)
            if score > 0:
                cell_id = str(fp.cell_id)
                cell_scores[cell_id] = cell_scores.get(cell_id, 0) + score

        if not cell_scores:
            raise LookupError("No matching fingerprints found for the given observations.")

        sorted_cells = sorted(cell_scores.items(), key=lambda x: x[1], reverse=True)
        best_cell_id = sorted_cells[0][0]
        best_score = sorted_cells[0][1]
        total_score = sum(s for _, s in sorted_cells)
        confidence = round(best_score / total_score, 4) if total_score > 0 else 0.0

        best_cell = self._cell_repo.get(UUID(best_cell_id))
        if best_cell is None:
            raise LookupError("Predicted cell not found.")

        candidates = []
        for cell_id, score in sorted_cells[:5]:
            cell = self._cell_repo.get(UUID(cell_id))
            if cell is not None:
                candidates.append(
                    CandidateCell(
                        cell_id=cell_id,
                        center_x=cell.center_x,
                        center_y=cell.center_y,
                        score=round(score / total_score, 4) if total_score > 0 else 0.0,
                    )
                )

        elapsed = time.perf_counter() - start
        logger.info(
            "Inference on floor %s: predicted=%s confidence=%.4f time=%.1fms",
            floor_id, best_cell_id, confidence, elapsed * 1000,
        )

        return InferenceResult(
            predicted_cell_id=best_cell_id,
            center_x=best_cell.center_x,
            center_y=best_cell.center_y,
            confidence=confidence,
            candidate_cells=candidates,
            model_version_id=str(model.id),
            inference_time_ms=round(elapsed * 1000, 2),
        )

    def _compute_similarity(
        self,
        query_observations: list[ObservationInput],
        fingerprint_id: UUID,
    ) -> float:
        fp_observations = self._obs_repo.list_by_fingerprint(fingerprint_id)
        if not fp_observations:
            return 0.0

        fp_rssi_map = {obs.bssid: obs.rssi for obs in fp_observations}
        similarity = 0.0
        for obs in query_observations:
            if obs.bssid in fp_rssi_map:
                diff = abs(obs.rssi - fp_rssi_map[obs.bssid])
                similarity += max(0, 100 - diff) / 100.0

        return similarity
