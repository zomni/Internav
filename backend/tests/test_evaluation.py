import pytest

from app.ai.evaluation import compute_metrics, top_k_accuracy


class TestTopKAccuracy:
    def test_perfect_top1(self):
        y_true = ["a", "b", "c"]
        y_proba = [
            {"a": 0.8, "b": 0.1, "c": 0.1},
            {"b": 0.7, "a": 0.2, "c": 0.1},
            {"c": 0.9, "a": 0.05, "b": 0.05},
        ]
        assert top_k_accuracy(y_true, y_proba, k=1) == 1.0

    def test_top3_all(self):
        y_true = ["a", "b", "c"]
        y_proba = [
            {"a": 0.4, "b": 0.3, "c": 0.3},
            {"b": 0.4, "c": 0.3, "a": 0.3},
            {"c": 0.4, "a": 0.3, "b": 0.3},
        ]
        assert top_k_accuracy(y_true, y_proba, k=3) == 1.0

    def test_empty(self):
        assert top_k_accuracy([], [], k=3) == 0.0

    def test_partial_top3(self):
        y_true = ["a", "d", "c"]
        y_proba = [
            {"a": 0.5, "b": 0.3, "c": 0.2},
            {"b": 0.6, "c": 0.3, "a": 0.1},
            {"c": 0.5, "b": 0.3, "a": 0.2},
        ]
        # second sample: 'd' not in top3 → 2/3
        assert top_k_accuracy(y_true, y_proba, k=3) == pytest.approx(round(2 / 3, 4))


class TestComputeMetrics:
    def test_perfect_prediction(self):
        y_true = ["a", "b", "c"]
        y_pred = ["a", "b", "c"]
        metrics = compute_metrics(y_true, y_pred)
        assert metrics["accuracy"] == 1.0
        assert metrics["macro_f1"] == 1.0
        assert metrics["num_classes"] == 3
        assert metrics["num_samples"] == 3

    def test_no_matches(self):
        y_true = ["a", "b"]
        y_pred = ["c", "d"]
        metrics = compute_metrics(y_true, y_pred)
        assert metrics["accuracy"] == 0.0
        assert metrics["macro_f1"] == 0.0

    def test_single_class(self):
        y_true = ["a", "a"]
        y_pred = ["a", "a"]
        metrics = compute_metrics(y_true, y_pred)
        assert metrics["accuracy"] == 1.0
        assert metrics["num_classes"] == 1

    def test_includes_top3_when_proba_provided(self):
        y_true = ["a", "b"]
        y_pred = ["a", "b"]
        y_proba = [
            {"a": 0.8, "b": 0.2},
            {"b": 0.7, "a": 0.3},
        ]
        metrics = compute_metrics(y_true, y_pred, y_pred_proba=y_proba)
        assert "top_3_accuracy" in metrics
        assert metrics["top_3_accuracy"] == 1.0

    def test_includes_inference_time(self):
        y_true = ["a", "b"]
        y_pred = ["a", "b"]
        metrics = compute_metrics(y_true, y_pred, inference_time_ms=3.5)
        assert metrics["mean_inference_time_ms"] == 3.5

    def test_empty_inputs(self):
        metrics = compute_metrics([], [])
        assert metrics["accuracy"] == 0.0
        assert metrics["num_samples"] == 0

    def test_per_class_metrics(self):
        y_true = ["a", "a", "b", "b"]
        y_pred = ["a", "b", "b", "a"]
        metrics = compute_metrics(y_true, y_pred)
        per_class = metrics["per_class"]
        assert "a" in per_class
        assert "b" in per_class
        # tp=1, fp=1, fn=1 for both classes → p=0.5, r=0.5, f1=0.5
        assert per_class["a"]["precision"] == 0.5
        assert per_class["a"]["recall"] == 0.5
        assert per_class["a"]["f1_score"] == 0.5
