import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import joblib


class ModelArtifactStorage:
    def __init__(self, base_path: str | Path):
        self._base_path = Path(base_path)
        self._base_path.mkdir(parents=True, exist_ok=True)

    def save_model(
        self,
        model_id: UUID,
        model_binary: object,
        metadata: dict[str, Any],
        feature_schema: dict[str, Any] | None = None,
    ) -> dict[str, str]:
        model_dir = self._base_path / str(model_id)
        model_dir.mkdir(parents=True, exist_ok=True)

        model_path = model_dir / "model.bin"
        joblib.dump(model_binary, model_path)
        with open(model_path, "rb") as f:
            checksum = hashlib.sha256(f.read()).hexdigest()

        metadata["checksum"] = checksum
        metadata["exported_at"] = datetime.now(UTC).isoformat()
        metadata_path = model_dir / "metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2, default=str)

        if feature_schema:
            schema_path = model_dir / "feature_schema.json"
            with open(schema_path, "w") as f:
                json.dump(feature_schema, f, indent=2, default=str)

        return {
            "model_path": str(model_path),
            "metadata_path": str(metadata_path),
            "checksum": checksum,
        }

    def load_model(self, model_id: UUID) -> tuple[object, dict[str, Any]]:
        model_dir = self._base_path / str(model_id)
        model_path = model_dir / "model.bin"
        metadata_path = model_dir / "metadata.json"

        if not model_path.exists():
            raise FileNotFoundError(f"Model artifact not found for {model_id}")

        model = joblib.load(model_path)
        with open(metadata_path) as f:
            metadata = json.load(f)
        return model, metadata

    def get_artifact_paths(self, model_id: UUID) -> dict[str, str]:
        model_dir = self._base_path / str(model_id)
        return {
            "model_path": str(model_dir / "model.bin"),
            "metadata_path": str(model_dir / "metadata.json"),
            "feature_schema_path": str(model_dir / "feature_schema.json"),
        }

    def build_mobile_bundle(self, model_id: UUID) -> dict[str, Any]:
        """Export the trained model as a JSON bundle consumable by the Android apps.

        The joblib/sklearn artifact cannot be parsed on Android, so reference
        vectors and the feature schema are exported as plain JSON. Cell labels
        come from ``feature_schema["classes"]`` (set at train time).
        """
        model_dir = self._base_path / str(model_id)
        model_path = model_dir / "model.bin"
        schema_path = model_dir / "feature_schema.json"

        if not model_path.exists():
            raise FileNotFoundError(f"Model artifact not found for {model_id}")
        if not schema_path.exists():
            raise RuntimeError("feature_schema.json is missing. Re-train the model.")

        model = joblib.load(model_path)
        with open(schema_path) as f:
            feature_schema = json.load(f)

        classes: list[str] = feature_schema.get("classes") or []
        fit_x = getattr(model, "_fit_X", None)
        fit_y = getattr(model, "_y", None)
        if fit_x is None or fit_y is None:
            raise RuntimeError("Model does not expose reference vectors.")

        references: list[dict[str, Any]] = []
        for i in range(len(fit_y)):
            class_idx = int(fit_y[i])
            cell_id = classes[class_idx] if 0 <= class_idx < len(classes) else None
            references.append({"cell_id": cell_id, "vector": [float(v) for v in fit_x[i]]})

        return {
            "feature_schema": feature_schema,
            "references": references,
        }

    def delete_model(self, model_id: UUID) -> None:
        model_dir = self._base_path / str(model_id)
        if model_dir.exists():
            import shutil

            shutil.rmtree(model_dir)
