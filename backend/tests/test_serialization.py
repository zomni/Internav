import json
import shutil
import tempfile
from pathlib import Path
from uuid import uuid4

import pytest
from sklearn.neighbors import KNeighborsClassifier

from app.ai.serialization import ModelArtifactStorage


@pytest.fixture()
def storage():
    tmp = Path(tempfile.mkdtemp())
    yield ModelArtifactStorage(str(tmp))
    shutil.rmtree(tmp)


class TestSaveModel:
    def test_saves_model_bin_and_metadata(self, storage):
        model_id = uuid4()
        model = KNeighborsClassifier(n_neighbors=1)
        model.fit([[0.0], [1.0]], [0, 1])
        result = storage.save_model(model_id, model, {"algorithm": "knn"})
        assert Path(result["model_path"]).exists()
        assert Path(result["metadata_path"]).exists()
        assert result["checksum"]

    def test_metadata_contains_checksum(self, storage):
        model_id = uuid4()
        model = KNeighborsClassifier(n_neighbors=1)
        model.fit([[0.0]], [0])
        result = storage.save_model(model_id, model, {"algorithm": "knn"})
        with open(result["metadata_path"]) as f:
            meta = json.load(f)
        assert meta["checksum"] == result["checksum"]

    def test_saves_feature_schema_when_provided(self, storage):
        model_id = uuid4()
        model = KNeighborsClassifier(n_neighbors=1)
        model.fit([[0.0]], [0])
        schema = {"version": "1.0", "bssid_vocabulary": ["BSSID:01"]}
        storage.save_model(model_id, model, {"algorithm": "knn"}, feature_schema=schema)
        schema_path = storage._base_path / str(model_id) / "feature_schema.json"
        assert schema_path.exists()
        with open(schema_path) as f:
            assert json.load(f) == schema


class TestLoadModel:
    def test_loads_saved_model(self, storage):
        model_id = uuid4()
        model = KNeighborsClassifier(n_neighbors=1)
        model.fit([[0.0], [1.0]], [0, 1])
        storage.save_model(model_id, model, {"algorithm": "knn"})
        loaded, meta = storage.load_model(model_id)
        assert isinstance(loaded, KNeighborsClassifier)
        assert meta["algorithm"] == "knn"

    def test_raises_on_missing(self, storage):
        with pytest.raises(FileNotFoundError):
            storage.load_model(uuid4())


class TestGetArtifactPaths:
    def test_returns_expected_keys(self, storage):
        model_id = uuid4()
        paths = storage.get_artifact_paths(model_id)
        assert "model_path" in paths
        assert "metadata_path" in paths
        assert "feature_schema_path" in paths

    def test_paths_point_to_model_dir(self, storage):
        model_id = uuid4()
        paths = storage.get_artifact_paths(model_id)
        expected_dir = storage._base_path / str(model_id)
        assert Path(paths["model_path"]).parent == expected_dir
        assert Path(paths["metadata_path"]).parent == expected_dir


class TestDeleteModel:
    def test_deletes_model_directory(self, storage):
        model_id = uuid4()
        model = KNeighborsClassifier(n_neighbors=1)
        model.fit([[0.0]], [0])
        storage.save_model(model_id, model, {"algorithm": "knn"})
        model_dir = storage._base_path / str(model_id)
        assert model_dir.exists()
        storage.delete_model(model_id)
        assert not model_dir.exists()

    def test_delete_nonexistent_does_not_raise(self, storage):
        storage.delete_model(uuid4())
