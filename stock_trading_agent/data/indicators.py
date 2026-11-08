"""Technical indicators and a compact feature snapshot for agents.

Everything is implemented with ``pandas``/``numpy`` only, so there is no
dependency on TA-Lib or other native libraries.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from numbers import Integral, Real

import numpy as np
import pandas as pd

from stock_trading_agent.data.types import PriceHistory


def _window(window: int) -> None:
    if isinstance(window, bool) or not isinstance(window, Integral) or window < 1:
        raise ValueError("Indicator window must be a positive integer.")


def _series(series: pd.Series, *, positive: bool = True) -> None:
    if (series.empty or not pd.api.types.is_numeric_dtype(series)
            or pd.api.types.is_bool_dtype(series) or pd.api.types.is_complex_dtype(series)
            or series.isna().any() or not np.isfinite(series.to_numpy(dtype=float)).all()
            or (positive and (series <= 0).any())):
        raise ValueError("Indicator input requires finite real prices, positive where applicable.")


def sma(series: pd.Series, window: int) -> pd.Series:
    _window(window)
    _series(series)
    return series.rolling(window=window, min_periods=1).mean()


def ema(series: pd.Series, window: int) -> pd.Series:
    _window(window)
    _series(series, positive=False)  # Also used for the signed MACD line.
    return series.ewm(span=window, adjust=False).mean()


def rsi(series: pd.Series, window: int = 14) -> pd.Series:
    """Wilder RSI: simple seed, recursive smoothing, NaN until window changes."""
    _window(window)
    _series(series)
    values = series.to_numpy(dtype=float)
    out = np.full(len(values), np.nan)
    if len(values) <= window:
        return pd.Series(out, index=series.index, name=series.name)
    changes = np.diff(values)
    gains, losses = np.maximum(changes, 0), np.maximum(-changes, 0)
    avg_gain, avg_loss = gains[:window].mean(), losses[:window].mean()
    for i in range(window, len(values)):
        if i > window:
            avg_gain = (avg_gain * (window - 1) + gains[i - 1]) / window
            avg_loss = (avg_loss * (window - 1) + losses[i - 1]) / window
        out[i] = 50. if avg_gain == avg_loss == 0 else 100. * avg_gain / (avg_gain + avg_loss)
    return pd.Series(out, index=series.index, name=series.name)


def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    _series(series)
    for window in (fast, slow, signal):
        _window(window)
    if fast >= slow:
        raise ValueError("MACD requires fast < slow.")
    macd_line = ema(series, fast) - ema(series, slow)
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line
    return pd.DataFrame({"macd": macd_line, "signal": signal_line, "hist": histogram})


def bollinger(series: pd.Series, window: int = 20, num_std: float = 2.0) -> pd.DataFrame:
    if isinstance(num_std, bool) or not isinstance(num_std, Real) or not np.isfinite(num_std) or num_std <= 0:
        raise ValueError("Bollinger width must be positive and finite.")
    mid = sma(series, window)
    std = series.rolling(window=window, min_periods=1).std(ddof=0)
    upper = mid + num_std * std
    lower = mid - num_std * std
    return pd.DataFrame({"bb_mid": mid, "bb_upper": upper, "bb_lower": lower})


def annualised_volatility(series: pd.Series, window: int = 20) -> float:
    _window(window)
    _series(series)
    daily = series.pct_change(fill_method=None).dropna().tail(window)
    if daily.empty:
        return 0.0
    return float(daily.std(ddof=0) * np.sqrt(252))


def atr(frame: pd.DataFrame, window: int = 14) -> pd.Series:
    """Average True Range — a volatility measure used for adaptive stops."""

    _window(window)
    for name in ("high", "low", "close"):
        _series(frame[name])
    high, low, close = frame["high"], frame["low"], frame["close"]
    if ((low > close) | (high < close) | (low > high)).any():
        raise ValueError("Invalid OHLC range for ATR.")
    prev_close = close.shift(1)
    true_range = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    return true_range.ewm(alpha=1 / window, adjust=False).mean()


def on_balance_volume(close: pd.Series, volume: pd.Series) -> pd.Series:
    """On-Balance Volume — cumulative volume signed by daily price direction."""

    _series(close)
    _series(volume, positive=False)
    if not close.index.equals(volume.index) or (volume < 0).any():
        raise ValueError("OBV requires aligned, nonnegative volume.")
    direction = np.sign(close.diff().fillna(0.0))
    return (direction * volume).cumsum()


@dataclass
class IndicatorSnapshot:
    """A compact, human-readable summary of the latest technical state.

    This is what we feed to the analyst agents instead of a giant raw frame.
    """

    symbol: str
    last_close: float
    sma_20: float
    sma_50: float
    ema_12: float
    rsi_14: float
    macd: float
    macd_signal: float
    macd_hist: float
    bb_upper: float
    bb_lower: float
    bb_pct: float  # position within the Bollinger band, 0=lower .. 1=upper
    pct_from_sma50: float
    annualised_vol: float
    atr_pct: float  # ATR as a fraction of price (adaptive stop width)
    volume_ratio: float  # recent volume vs. its longer-run average
    obv_trend: str  # "accumulation" | "distribution" | "flat"
    trend: str  # "uptrend" | "downtrend" | "sideways"
    momentum: str  # "overbought" | "oversold" | "neutral"

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        for key, value in asdict(self).items():
            if key in {"symbol", "obv_trend", "trend", "momentum"}:
                continue
            if isinstance(value, bool) or not isinstance(value, Real) or not np.isfinite(value):
                raise ValueError(f"Invalid indicator {key}: finite real value required.")
        if not 0 <= self.rsi_14 <= 100 or min(self.annualised_vol, self.atr_pct, self.volume_ratio) < 0:
            raise ValueError("Indicator RSI or volatility/volume outside its valid range.")
        if min(self.last_close, self.sma_20, self.sma_50, self.ema_12) <= 0:
            raise ValueError("Indicator prices must be positive.")

    def to_dict(self) -> dict:
        return asdict(self)


def compute_indicators(history: PriceHistory) -> IndicatorSnapshot:
    """Compute a full :class:`IndicatorSnapshot` from a price history."""

    frame = history.frame
    history.validate()
    if len(history) < 50:
        raise ValueError("Indicator snapshot requires at least 50 complete bars.")
    close = frame["close"]
    volume = frame["volume"]
    sma20 = sma(close, 20)
    sma50 = sma(close, 50)
    ema12 = ema(close, 12)
    rsi14 = rsi(close, 14)
    macd_df = macd(close)
    bb = bollinger(close)

    last_close = float(close.iloc[-1])
    last_sma50 = float(sma50.iloc[-1])
    pct_from_sma50 = (last_close - last_sma50) / last_sma50 * 100 if last_sma50 else 0.0

    bb_upper = float(bb["bb_upper"].iloc[-1])
    bb_lower = float(bb["bb_lower"].iloc[-1])
    band = bb_upper - bb_lower
    bb_pct = (last_close - bb_lower) / band if band > 1e-9 else 0.5

    atr_series = atr(frame)
    atr_pct = float(atr_series.iloc[-1]) / last_close if last_close else 0.0

    recent_vol = float(volume.tail(10).mean())
    base_vol = float(volume.tail(50).mean()) or 1.0
    volume_ratio = recent_vol / base_vol if base_vol else 1.0

    obv = on_balance_volume(close, volume)
    obv_slope = float(obv.iloc[-1] - obv.iloc[max(0, len(obv) - 20)])
    if obv_slope > 0:
        obv_trend = "accumulation"
    elif obv_slope < 0:
        obv_trend = "distribution"
    else:
        obv_trend = "flat"

    if float(sma20.iloc[-1]) > last_sma50 * 1.01:
        trend = "uptrend"
    elif float(sma20.iloc[-1]) < last_sma50 * 0.99:
        trend = "downtrend"
    else:
        trend = "sideways"

    last_rsi = float(rsi14.iloc[-1])
    if last_rsi >= 70:
        momentum = "overbought"
    elif last_rsi <= 30:
        momentum = "oversold"
    else:
        momentum = "neutral"

    return IndicatorSnapshot(
        symbol=history.symbol,
        last_close=round(last_close, 4),
        sma_20=round(float(sma20.iloc[-1]), 4),
        sma_50=round(last_sma50, 4),
        ema_12=round(float(ema12.iloc[-1]), 4),
        rsi_14=round(last_rsi, 2),
        macd=round(float(macd_df["macd"].iloc[-1]), 4),
        macd_signal=round(float(macd_df["signal"].iloc[-1]), 4),
        macd_hist=round(float(macd_df["hist"].iloc[-1]), 4),
        bb_upper=round(bb_upper, 4),
        bb_lower=round(bb_lower, 4),
        bb_pct=round(bb_pct, 4),
        pct_from_sma50=round(pct_from_sma50, 2),
        annualised_vol=round(annualised_volatility(close), 4),
        atr_pct=round(atr_pct, 4),
        volume_ratio=round(volume_ratio, 3),
        obv_trend=obv_trend,
        trend=trend,
        momentum=momentum,
    )
