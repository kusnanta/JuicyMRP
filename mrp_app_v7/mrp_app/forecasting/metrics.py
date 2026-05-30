"""forecasting/metrics.py — MAPE, MAE, RMSE, and Accuracy."""
from __future__ import annotations

import numpy as np


def mape(actual: np.ndarray, predicted: np.ndarray) -> float:
    """Mean Absolute Percentage Error (%). Skips zero-actual rows."""
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    mask = actual > 0
    if mask.sum() == 0:
        return float("nan")
    return float(np.mean(np.abs((actual[mask] - predicted[mask]) / actual[mask])) * 100)


def accuracy(actual: np.ndarray, predicted: np.ndarray) -> float:
    """Forecast accuracy as 100% - MAPE. Clipped to [0, 100]."""
    m = mape(actual, predicted)
    if np.isnan(m):
        return float("nan")
    return round(max(0.0, min(100.0, 100.0 - m)), 1)


def mae(actual: np.ndarray, predicted: np.ndarray) -> float:
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    return float(np.mean(np.abs(actual - predicted)))


def rmse(actual: np.ndarray, predicted: np.ndarray) -> float:
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    return float(np.sqrt(np.mean((actual - predicted) ** 2)))
