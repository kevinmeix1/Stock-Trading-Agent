"""Core market data structures."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class OHLCV:
    """A single Open/High/Low/Close/Volume bar."""

    date: date
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class PriceHistory:
    """A symbol's price history wrapped around a tidy ``pandas`` frame.

    The frame is indexed by date and always contains the columns
    ``open, high, low, close, volume``.
    """

    symbol: str
    frame: pd.DataFrame

    def __post_init__(self) -> None:
        self.frame = self.frame.copy()
        if not isinstance(self.frame.index, pd.DatetimeIndex):
            self.frame.index = pd.to_datetime(self.frame.index)
        self.frame = self.frame.sort_index()
        self.validate()

    def validate(self) -> None:
        """Reject corrupt bars rather than smoothing over them in indicators."""
        required = {"open", "high", "low", "close", "volume"}
        missing = required - set(self.frame.columns)
        if missing:
            raise ValueError(f"PriceHistory for {self.symbol} missing columns: {sorted(missing)}")
        if self.frame.empty or not self.frame.columns.is_unique:
            raise ValueError("PriceHistory requires nonempty, uniquely named OHLCV columns.")
        index = self.frame.index
        if (not isinstance(index, pd.DatetimeIndex) or index.hasnans
                or not index.is_unique or not index.is_monotonic_increasing):
            raise ValueError("PriceHistory dates must be valid, unique and chronological.")
        for name in required:
            series = self.frame[name]
            if (not pd.api.types.is_numeric_dtype(series) or pd.api.types.is_bool_dtype(series)
                    or pd.api.types.is_complex_dtype(series) or series.isna().any()
                    or not np.isfinite(series.to_numpy(dtype=float)).all()):
                raise ValueError(f"PriceHistory {name} must contain finite real numbers.")
        prices = self.frame[["open", "high", "low", "close"]]
        if (prices <= 0).any().any() or (self.frame["volume"] < 0).any():
            raise ValueError("Prices must be positive and volume nonnegative.")
        if ((self.frame["high"] < prices.max(axis=1)).any()
                or (self.frame["low"] > prices.min(axis=1)).any()):
            raise ValueError("OHLC bars must satisfy low <= open/close <= high.")

    def __len__(self) -> int:
        return len(self.frame)

    @property
    def latest_close(self) -> float:
        return float(self.frame["close"].iloc[-1])

    @property
    def start(self) -> pd.Timestamp:
        return self.frame.index[0]

    @property
    def end(self) -> pd.Timestamp:
        return self.frame.index[-1]

    def window(self, lookback: int) -> pd.DataFrame:
        """Return the trailing ``lookback`` rows."""

        return self.frame.tail(lookback)

    def returns(self) -> pd.Series:
        """Simple daily returns of the close price."""

        return self.frame["close"].pct_change().dropna()
