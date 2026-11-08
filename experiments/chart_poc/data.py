"""Frozen, validated retrospective daily prices; no application imports."""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class Series:
    symbol: str
    dates: tuple[str, ...]
    ohlc: np.ndarray
    close: np.ndarray


def load_data(directory: Path) -> tuple[dict[str, Series], dict]:
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    result = {}
    for item in manifest["symbols"]:
        path = directory / item["file"]
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != item["sha256"]:
            raise ValueError("Snapshot checksum mismatch: " + item["symbol"])
        rows = list(csv.DictReader(raw.decode("utf-8").splitlines()))
        dates = tuple(r["date"] for r in rows)
        if (
            len(dates) != item["rows"]
            or len(set(dates)) != len(dates)
            or tuple(sorted(dates)) != dates
        ):
            raise ValueError("Invalid row count/dates")
        from datetime import date

        for value in dates:
            date.fromisoformat(value)
        if dates[0] != item["start"] or dates[-1] != item["end"]:
            raise ValueError("Snapshot period mismatch")
        values = np.array(
            [
                [float(r[k]) for k in ("open", "high", "low", "close", "volume", "adj_close")]
                for r in rows
            ]
        )
        if (
            not np.isfinite(values).all()
            or (values[:, :4] <= 0).any()
            or (values[:, 5] <= 0).any()
            or (values[:, 4] < 0).any()
        ):
            raise ValueError("Non-finite or non-positive prices/negative volume")
        opening, high, low, closing = values[:, :4].T
        if (
            (high < np.maximum(opening, closing)).any()
            or (low > np.minimum(opening, closing)).any()
            or (high < low).any()
        ):
            raise ValueError("Invalid OHLC geometry")
        adjusted = values[:, :4] * (values[:, 5] / closing)[:, None]
        adjusted.setflags(write=False)
        close = adjusted[:, 3]
        result[item["symbol"]] = Series(item["symbol"], dates, adjusted, close)
    if set(result) != {"AAPL", "IBM", "MSFT"}:
        raise ValueError("Unexpected instrument universe")
    if len({s.dates for s in result.values()}) != 1:
        raise ValueError("Trading-date grids differ: do not silently align or forward-fill")
    return result, manifest
