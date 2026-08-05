import json
import logging
import time
from uuid import UUID

import numpy as np

from app.ai.dataset_export import DatasetExportService
from app.ai.evaluation import compute_metrics
from app.ai.knn_model import KNNTrainer
from app.ai.serialization import ModelArtifactStorage
from app.domain.entities.model_version import ModelVersion, ModelVersionStatus
from app.domain.events import DomainEvent, EventBus, EventType
from app.repositories.fingerprint_repository import FingerprintRepository
from app.repositories.model_version_repository import ModelVersionRepository

logger = logging.getLogger("app.training")


def _train_val_split(
    X: np.ndarray, y: list[str], val_ratio: float = 0.2, seed: int = 42
) -> tuple[np.ndarray, list[str], np.ndarray, list[str]]:
    rng = np.random.default_rng(seed)
    indices = rng.permutation(len(y))
    split = max(1, int(len(y) * (1 - val_ratio)))
    train_idx = indices[:split]
    val_idx = indices[split:]
    return X[train_idx], [y[i] for i in train_idx], X[val_idx], [y[i] for i in val_idx]


class TrainingPipelineService:
    def __init__(
        self,
        model_version_repository: ModelVersionRepository,
        fingerprint_repository: FingerprintRepository,
        dataset_export_service: DatasetExportService,
        model_storage: ModelArtifactStorage,
    ) -> None:
        self._model_version_repo = model_version_repository
        self._fingerprint_repo = fingerprint_repository
        self._dataset_export = dataset_export_service
        self._storage = model_storage

    def train(self, model_version_id: UUID) -> ModelVersion:
        mv = self._model_version_repo.get(model_version_id)
        if mv is None:
            raise LookupError("ModelVersion not found.")
        if mv.status != ModelVersionStatus.TRAINING:
            raise ValueError(f"Cannot train ModelVersion in {mv.status.value} status.")

        logger.info("Training started for model %s on floor %s", mv.id, mv.floor_id)
        EventBus.publish(
            DomainEvent(EventType.TRAINING_STARTED, mv.id, {"model_version_id": str(mv.id)})
        )

        start = time.perf_counter()

        export = self._dataset_export.export_dataset(mv.dataset_id)
        samples = export["samples"]
        bssid_vocabulary = export["bssid_vocabulary"]

        if not samples:
            raise ValueError("No samples in dataset. Cannot train.")

        trainer = KNNTrainer()
        X = trainer.build_feature_matrix(samples, bssid_vocabulary)
        cell_ids = [s["cell_id"] for s in samples]

        # Train/validation split (80/20); fall back to full data if too few samples
        if len(cell_ids) >= 5:
            X_train, y_train, X_val, y_val = _train_val_split(X, cell_ids)
        else:
            X_train, y_train, X_val, y_val = X, cell_ids, X, cell_ids

        train_info = trainer.train(X_train, y_train)

        # Evaluate on validation set
        y_pred, _ = trainer.predict(X_val)

        # Build per-sample probability dicts for top-k accuracy
        proba_model = getattr(trainer.get_model(), "predict_proba", None)
        y_pred_proba: list[dict[str, float]] | None = None
        if proba_model and len(trainer.get_model().classes_) > 0:
            raw_proba = trainer.get_model().predict_proba(X_val)
            y_pred_proba = [
                {str(cls): float(p[i]) for i, cls in enumerate(trainer.get_model().classes_)}
                for p in raw_proba
            ]

        # Measure inference time on validation set
        inference_start = time.perf_counter()
        trainer.predict(X_val)
        inference_time_ms = round(
            (time.perf_counter() - inference_start) / max(len(y_val), 1) * 1000.0, 4
        )

        metrics = compute_metrics(y_val, y_pred, y_pred_proba, inference_time_ms)

        feature_schema = {
            "version": "1.0",
            "bssid_vocabulary": bssid_vocabulary,
            "feature_count": len(bssid_vocabulary),
            "normalization": "min_max_100",
            "missing_ap_value": 0.0,
            "classes": train_info["classes"],
        }

        metadata = {
            "algorithm": mv.algorithm,
            "dataset_id": str(mv.dataset_id),
            "floor_id": str(mv.floor_id),
            "dataset_version": export["dataset_version"],
            "training_timestamp": time.time(),
            "software_version": "0.1.0",
            "bssid_vocabulary_size": len(bssid_vocabulary),
            "num_samples": len(samples),
            "num_train": len(y_train),
            "num_val": len(y_val),
            "num_cells": len(train_info["classes"]),
        }

        result = self._storage.save_model(mv.id, trainer.get_model(), metadata, feature_schema)
        training_time = round(time.perf_counter() - start, 4)

        mv.hyperparameters = json.dumps(
            {"n_neighbors": train_info["n_neighbors"], "weights": "distance"}
        )
        mv.metrics = json.dumps(metrics)
        mv.training_time = training_time
        mv.checksum = result["checksum"]

        mv.transition_to(ModelVersionStatus.READY)
        saved = self._model_version_repo.update(mv)

        logger.info(
            "Training completed for model %s: accuracy=%.4f, time=%.2fs",
            mv.id,
            metrics.get("accuracy", 0),
            training_time,
        )

        EventBus.publish(
            DomainEvent(
                EventType.TRAINING_COMPLETED,
                mv.id,
                {
                    "model_version_id": str(mv.id),
                    "metrics": metrics,
                    "training_time": training_time,
                },
            )
        )
        EventBus.publish(
            DomainEvent(
                EventType.MODEL_READY,
                mv.id,
                {
                    "model_version_id": str(mv.id),
                    "metrics": metrics,
                },
            )
        )

        return saved

    def get_artifact_paths(self, model_version_id: UUID) -> dict[str, str]:
        return self._storage.get_artifact_paths(model_version_id)

    def get_mobile_bundle(self, model_version_id: UUID) -> dict:
        mv = self._model_version_repo.get(model_version_id)
        if mv is None:
            raise LookupError("ModelVersion not found.")
        if mv.status not in (
            ModelVersionStatus.READY,
            ModelVersionStatus.PUBLISHED,
            ModelVersionStatus.ARCHIVED,
        ):
            raise ValueError(f"No mobile bundle for ModelVersion in {mv.status.value} status.")
        try:
            return self._storage.build_mobile_bundle(model_version_id)
        except (FileNotFoundError, RuntimeError) as exc:
            raise RuntimeError(str(exc)) from exc
