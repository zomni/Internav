from typing import Any

import numpy as np
from sklearn.neighbors import KNeighborsClassifier


class KNNTrainer:
    def __init__(self, n_neighbors: int = 3, weights: str = "distance"):
        self._n_neighbors = n_neighbors
        self._weights = weights
        self._model: KNeighborsClassifier | None = None
        self._bssid_vocabulary: list[str] = []
        self._cell_labels: list[str] = []

    def build_feature_matrix(self, samples: list[dict[str, Any]], bssid_vocabulary: list[str]) -> np.ndarray:
        self._bssid_vocabulary = bssid_vocabulary
        num_samples = len(samples)
        num_features = len(bssid_vocabulary)
        matrix = np.zeros((num_samples, num_features), dtype=np.float32)

        for i, sample in enumerate(samples):
            rssi_map = {obs["bssid"]: obs["rssi"] for obs in sample["observations"]}
            for j, bssid in enumerate(bssid_vocabulary):
                rssi = rssi_map.get(bssid)
                if rssi is not None:
                    matrix[i, j] = (rssi + 100) / 100.0
        return matrix

    def train(self, X: np.ndarray, y: list[str]) -> dict[str, Any]:
        self._cell_labels = sorted(set(y))
        label_to_idx = {label: idx for idx, label in enumerate(self._cell_labels)}
        y_indices = [label_to_idx[label] for label in y]

        self._model = KNeighborsClassifier(
            n_neighbors=min(self._n_neighbors, len(set(y_indices))),
            weights=self._weights,
        )
        self._model.fit(X, y_indices)
        return {"classes": self._cell_labels, "n_neighbors": self._model.n_neighbors}

    def predict(self, X: np.ndarray) -> tuple[list[str], list[float]]:
        if self._model is None:
            raise RuntimeError("Model not trained.")
        indices = self._model.predict(X)
        probs = self._model.predict_proba(X)
        confidences = [float(p.max()) for p in probs]
        return [self._cell_labels[i] for i in indices], confidences

    def get_model(self) -> KNeighborsClassifier | None:
        return self._model
