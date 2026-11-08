"""STUMPY MASS forecasts from an immutable training library."""

from __future__ import annotations

import numpy as np
import stumpy


def select_neighbors(
    log_library: np.ndarray, query: np.ndarray, horizon: int, k: int
) -> list[dict]:
    m = len(query)
    if len(log_library) < m + horizon or not np.isfinite(query).all() or np.std(query) < 1e-12:
        raise ValueError("Insufficient library or constant/non-finite query")
    profile = np.asarray(stumpy.mass(query, log_library), dtype=float)
    eligible = np.arange(len(profile)) <= len(log_library) - m - horizon
    # STUMPY defines constant-window distances specially; they are not analogues here.
    for i in np.flatnonzero(eligible):
        if np.std(log_library[i : i + m]) < 1e-12:
            eligible[i] = False
    order = np.lexsort((np.arange(len(profile)), np.where(eligible, profile, np.inf)))
    selected = []
    for start in order:
        start = int(start)
        if not eligible[start] or not np.isfinite(profile[start]):
            continue
        end = start + m - 1
        if any(not (end + horizon < x["start"] or start > x["outcome_end"]) for x in selected):
            continue
        selected.append(
            {
                "start": start,
                "end": end,
                "outcome_end": end + horizon,
                "distance": float(profile[start]),
                "forward_log_return": float(log_library[end + horizon] - log_library[end]),
            }
        )
        if len(selected) == k:
            break
    if len(selected) != k:
        raise ValueError("Not enough disjoint historical matches")
    return selected


class Predictor:
    def __init__(self, training_close: np.ndarray, window: int, horizon: int, k: int):
        if not np.isfinite(training_close).all() or (training_close <= 0).any():
            raise ValueError("Invalid training prices")
        self.library = np.log(np.array(training_close, dtype=float, copy=True))
        self.window, self.horizon, self.k = window, horizon, k

    def predict(self, available_close: np.ndarray) -> dict:
        if len(available_close) < self.window:
            raise ValueError("Insufficient closed history")
        close = np.asarray(available_close[-self.window :], dtype=float)
        if not np.isfinite(close).all() or (close <= 0).any():
            raise ValueError("Invalid query prices")
        # Entire neighbour feature+outcome interval ends before query begins.
        library = self.library[: min(len(self.library), len(available_close) - self.window)]
        matches = select_neighbors(library, np.log(close), self.horizon, self.k)
        forecast = float(np.mean([x["forward_log_return"] for x in matches]))
        return {
            "mass": int(np.sign(forecast)),
            "mass_expected_log_return": forecast,
            "trend": int(np.sign(np.mean(close[-20:]) - np.mean(close[-50:]))),
            "momentum": int(np.sign(close[-1] / close[-21] - 1)),
            "always_positive": 1,
            "matches": matches,
        }
