import numpy as np
import pytest

from app.ai.knn_model import KNNTrainer


def _make_sample(
    cell_id: str,
    bssid_rssi: list[tuple[str, int]],
) -> dict:
    return {
        "cell_id": cell_id,
        "observations": [
            {"bssid": bssid, "ssid": "", "rssi": rssi, "frequency": 2412}
            for bssid, rssi in bssid_rssi
        ],
    }


class TestBuildFeatureMatrix:
    def test_basic_matrix_shape(self):
        vocab = ["AA:BB:CC:DD:EE:01", "AA:BB:CC:DD:EE:02", "AA:BB:CC:DD:EE:03"]
        samples = [
            _make_sample("cell_1", [("AA:BB:CC:DD:EE:01", -50), ("AA:BB:CC:DD:EE:02", -60)]),
            _make_sample("cell_2", [("AA:BB:CC:DD:EE:02", -55), ("AA:BB:CC:DD:EE:03", -70)]),
        ]
        trainer = KNNTrainer()
        X = trainer.build_feature_matrix(samples, vocab)
        assert X.shape == (2, 3)

    def test_rssi_normalization(self):
        vocab = ["AA:BB:CC:DD:EE:01"]
        samples = [
            _make_sample("cell_1", [("AA:BB:CC:DD:EE:01", -50)]),
        ]
        trainer = KNNTrainer()
        X = trainer.build_feature_matrix(samples, vocab)
        # ( -50 + 100 ) / 100 = 0.5
        assert np.isclose(X[0, 0], 0.5)

    def test_missing_ap_defaults_to_zero(self):
        vocab = ["AA:BB:CC:DD:EE:01", "AA:BB:CC:DD:EE:02"]
        samples = [
            _make_sample("cell_1", [("AA:BB:CC:DD:EE:01", -50)]),
        ]
        trainer = KNNTrainer()
        X = trainer.build_feature_matrix(samples, vocab)
        # Second BSSID not in observations → should be 0.0
        assert X[0, 1] == 0.0

    def test_empty_samples(self):
        trainer = KNNTrainer()
        X = trainer.build_feature_matrix([], ["AA:BB:CC:DD:EE:01"])
        assert X.shape == (0, 1)


class TestTrain:
    def test_train_creates_model(self):
        vocab = ["BSSID:01", "BSSID:02"]
        samples = [
            _make_sample("cell_a", [("BSSID:01", -50)]),
            _make_sample("cell_b", [("BSSID:02", -60)]),
            _make_sample("cell_a", [("BSSID:01", -45), ("BSSID:02", -65)]),
        ]
        trainer = KNNTrainer()
        X = trainer.build_feature_matrix(samples, vocab)
        y = [s["cell_id"] for s in samples]
        info = trainer.train(X, y)
        assert info["classes"] == ["cell_a", "cell_b"]
        assert info["n_neighbors"] > 0
        assert trainer.get_model() is not None

    def test_train_single_class(self):
        vocab = ["BSSID:01"]
        samples = [
            _make_sample("cell_x", [("BSSID:01", -50)]),
            _make_sample("cell_x", [("BSSID:01", -55)]),
        ]
        trainer = KNNTrainer()
        X = trainer.build_feature_matrix(samples, vocab)
        y = [s["cell_id"] for s in samples]
        info = trainer.train(X, y)
        assert info["classes"] == ["cell_x"]
        assert info["n_neighbors"] == 1

    def test_neighbors_capped_by_classes(self):
        trainer = KNNTrainer(n_neighbors=10)
        vocab = ["BSSID:01"]
        samples = [
            _make_sample("cell_a", [("BSSID:01", -50)]),
            _make_sample("cell_b", [("BSSID:01", -55)]),
        ]
        X = trainer.build_feature_matrix(samples, vocab)
        y = [s["cell_id"] for s in samples]
        info = trainer.train(X, y)
        assert info["n_neighbors"] <= 2


class TestPredict:
    def test_predict_returns_labels_and_confidences(self):
        vocab = ["BSSID:01", "BSSID:02"]
        samples = [
            _make_sample("cell_a", [("BSSID:01", -50)]),
            _make_sample("cell_b", [("BSSID:02", -60)]),
            _make_sample("cell_a", [("BSSID:01", -45)]),
            _make_sample("cell_b", [("BSSID:02", -65)]),
        ]
        trainer = KNNTrainer()
        X = trainer.build_feature_matrix(samples, vocab)
        y = [s["cell_id"] for s in samples]
        trainer.train(X, y)

        preds, confs = trainer.predict(X)
        assert len(preds) == 4
        assert len(confs) == 4
        assert all(0.0 <= c <= 1.0 for c in confs)

    def test_predict_before_train_raises(self):
        trainer = KNNTrainer()
        with pytest.raises(RuntimeError, match="not trained"):
            trainer.predict(np.zeros((1, 3)))
