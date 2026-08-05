from typing import Any

import numpy as np


def top_k_accuracy(y_true: list[str], y_pred_proba: list[dict[str, float]], k: int = 3) -> float:
    total = len(y_true)
    if total == 0:
        return 0.0
    hits = 0
    for true_label, proba in zip(y_true, y_pred_proba):
        top_k = sorted(proba, key=proba.get, reverse=True)[:k]
        if true_label in top_k:
            hits += 1
    return round(hits / total, 4)


def compute_metrics(
    y_true: list[str],
    y_pred: list[str],
    y_pred_proba: list[dict[str, float]] | None = None,
    inference_time_ms: float | None = None,
) -> dict[str, Any]:
    total = len(y_true)
    correct = sum(1 for t, p in zip(y_true, y_pred) if t == p)
    accuracy = round(correct / total, 4) if total > 0 else 0.0

    cell_labels = sorted(set(y_true) | set(y_pred))
    confusion: dict[str, dict[str, int]] = {label: {l2: 0 for l2 in cell_labels} for label in cell_labels}
    for t, p in zip(y_true, y_pred):
        confusion[t][p] += 1

    precision_recall = {}
    for label in cell_labels:
        tp = confusion[label][label]
        fp = sum(confusion[l][label] for l in cell_labels if l != label)
        fn = sum(confusion[label][l] for l in cell_labels if l != label)
        precision = round(tp / (tp + fp), 4) if (tp + fp) > 0 else 0.0
        recall = round(tp / (tp + fn), 4) if (tp + fn) > 0 else 0.0
        f1 = round(2 * precision * recall / (precision + recall), 4) if (precision + recall) > 0 else 0.0
        precision_recall[label] = {
            "precision": precision,
            "recall": recall,
            "f1_score": f1,
        }

    macro_f1 = round(float(np.mean([v["f1_score"] for v in precision_recall.values()])), 4) if precision_recall else 0.0
    result: dict[str, Any] = {
        "accuracy": accuracy,
        "macro_f1": macro_f1,
        "num_classes": len(cell_labels),
        "num_samples": total,
        "per_class": precision_recall,
    }

    if y_pred_proba:
        result["top_3_accuracy"] = top_k_accuracy(y_true, y_pred_proba, k=3)
    if inference_time_ms is not None:
        result["mean_inference_time_ms"] = inference_time_ms

    return result
