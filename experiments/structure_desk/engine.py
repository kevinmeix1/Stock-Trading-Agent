"""Causal, descriptive daily chart state; no forecasting or decision pipeline."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from numbers import Real

import numpy as np
import pandas as pd

SPAN = 3


def validate(frame: pd.DataFrame) -> None:
    required = ["open", "high", "low", "close", "volume"]
    if not frame.columns.is_unique or any(key not in frame for key in required):
        raise ValueError("Unique OHLCV columns required.")
    if (
        len(frame) < 50
        or not isinstance(frame.index, pd.DatetimeIndex)
        or frame.index.hasnans
        or not frame.index.is_unique
        or not frame.index.is_monotonic_increasing
    ):
        raise ValueError("At least 50 complete bars with unique chronological dates required.")
    for key in required:
        col = frame[key]
        if (
            not pd.api.types.is_numeric_dtype(col)
            or pd.api.types.is_bool_dtype(col)
            or pd.api.types.is_complex_dtype(col)
            or col.isna().any()
            or not np.isfinite(col.to_numpy(dtype=float)).all()
        ):
            raise ValueError("Finite real OHLCV values required.")
    prices = frame[required[:4]]
    if (prices <= 0).any().any() or (frame.volume < 0).any():
        raise ValueError("Prices must be positive; volume must be nonnegative.")
    if (frame.high < prices.max(axis=1)).any() or (frame.low > prices.min(axis=1)).any():
        raise ValueError("Invalid OHLC range.")


def wilder(values: np.ndarray, period: int) -> np.ndarray:
    """SMA seed, then Wilder recursion; unavailable prefix stays NaN."""
    result = np.full(len(values), np.nan)
    if len(values) < period:
        return result
    result[period - 1] = np.mean(values[:period])
    for i in range(period, len(values)):
        result[i] = (result[i - 1] * (period - 1) + values[i]) / period
    return result


def indicator_series(frame: pd.DataFrame) -> pd.DataFrame:
    close = frame.close.astype(float)
    changes = np.diff(close.to_numpy())
    gain = wilder(np.maximum(changes, 0.0), 14)
    loss = wilder(np.maximum(-changes, 0.0), 14)
    denominator = gain + loss
    ratio = np.divide(gain, denominator, out=np.full(len(gain), np.nan), where=denominator > 0)
    rsi = np.concatenate([[np.nan], np.where(denominator == 0, 50.0, 100.0 * ratio)])
    macd = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
    signal = macd.ewm(span=9, adjust=False).mean()
    previous = close.shift(1)
    tr = pd.concat(
        [frame.high - frame.low, (frame.high - previous).abs(), (frame.low - previous).abs()],
        axis=1,
    ).max(axis=1)
    output = pd.DataFrame(
        {
            "rsi14": rsi,
            "atr14": wilder(tr.to_numpy(), 14),
            "macd": macd,
            "macd_signal": signal,
            "macd_hist": macd - signal,
        },
        index=frame.index,
    )
    for window in (20, 50, 200):
        output[f"sma{window}"] = close.rolling(window, min_periods=window).mean()
    return output


@dataclass(frozen=True)
class Swing:
    index: int
    confirmed_index: int
    kind: str
    price: float
    label: str


def confirmed_swings(frame: pd.DataFrame) -> list[Swing]:
    """Strict 3-left/3-right pivots. Outside-bar dual pivots are ambiguous."""
    result: list[Swing] = []
    prior: dict[str, float] = {}
    for i in range(SPAN, len(frame) - SPAN):
        window = frame.iloc[i - SPAN : i + SPAN + 1]
        high = float(frame.high.iloc[i])
        low = float(frame.low.iloc[i])
        is_high = high == window.high.max() and (window.high == high).sum() == 1
        is_low = low == window.low.min() and (window.low == low).sum() == 1
        if is_high == is_low:
            continue
        kind, price = ("H", high) if is_high else ("L", low)
        previous = prior.get(kind)
        label = (
            kind
            if previous is None
            else (
                ("HH" if price > previous else "LH" if price < previous else "EH")
                if kind == "H"
                else ("HL" if price > previous else "LL" if price < previous else "EL")
            )
        )
        result.append(Swing(i, i + SPAN, kind, price, label))
        prior[kind] = price
    return result


def structure_breaks(frame: pd.DataFrame, swings: list[Swing]) -> tuple[list[dict], str]:
    events: list[dict] = []
    latest: dict[str, Swing] = {}
    broken: set[tuple[str, int]] = set()
    bias = "NEUTRAL"
    pending = iter(swings)
    next_swing = next(pending, None)
    for i in range(1, len(frame)):
        while next_swing and next_swing.confirmed_index <= i:
            latest[next_swing.kind] = next_swing
            next_swing = next(pending, None)
        for kind, direction in (("H", "BULLISH"), ("L", "BEARISH")):
            level = latest.get(kind)
            if not level or (kind, level.index) in broken:
                continue
            previous, current = float(frame.close.iloc[i - 1]), float(frame.close.iloc[i])
            crosses = (
                previous <= level.price < current
                if kind == "H"
                else previous >= level.price > current
            )
            if crosses:
                event = "BOS" if bias in {"NEUTRAL", direction} else "CHoCH"
                events.append(
                    {
                        "event": event,
                        "direction": direction,
                        "index": i,
                        "level": level.price,
                        "pivot_index": level.index,
                        "initial": bias == "NEUTRAL",
                    }
                )
                broken.add((kind, level.index))
                bias = direction
    return events, bias


def price_zones(frame: pd.DataFrame, swings: list[Swing], atr_series: pd.Series) -> list[dict]:
    """Freeze at second confirmation; a close break permanently invalidates a cluster."""
    atr = float(atr_series.iloc[-1])
    if not np.isfinite(atr) or atr <= 0:
        return []
    close = float(frame.close.iloc[-1])
    output: list[dict] = []
    for kind, role in (("L", "support"), ("H", "resistance")):
        clusters: list[dict] = []

        def invalidated(cluster: dict, until: int, pivot_kind: str = kind) -> bool:
            closes = frame.close.iloc[cluster["swings"][0].index + 1 : until + 1]
            return bool(
                (closes < cluster["lower"]).any()
                if pivot_kind == "L"
                else (closes > cluster["upper"]).any()
            )

        for swing in swings:
            at_confirmation = float(atr_series.iloc[swing.confirmed_index])
            if swing.kind != kind or not np.isfinite(at_confirmation) or at_confirmation <= 0:
                continue
            cluster = None
            for candidate in clusters:
                if invalidated(candidate, swing.confirmed_index):
                    continue
                if swing.index - candidate["swings"][-1].index < 5:
                    continue
                fits = (
                    candidate["lower"] <= swing.price <= candidate["upper"]
                    if len(candidate["swings"]) >= 2
                    else abs(candidate["swings"][0].price - swing.price) <= 0.5 * at_confirmation
                )
                if fits:
                    cluster = candidate
                    break
            if cluster is None:
                clusters.append(
                    {
                        "swings": [swing],
                        "lower": swing.price - 0.25 * at_confirmation,
                        "upper": swing.price + 0.25 * at_confirmation,
                        "established_index": None,
                        "atr_at_establishment": None,
                    }
                )
            else:
                if len(cluster["swings"]) == 1:
                    seed = cluster["swings"][0].price
                    cluster.update(
                        lower=min(seed, swing.price) - 0.25 * at_confirmation,
                        upper=max(seed, swing.price) + 0.25 * at_confirmation,
                        established_index=swing.confirmed_index,
                        atr_at_establishment=at_confirmation,
                    )
                cluster["swings"].append(swing)
        for cluster in clusters:
            touches = cluster["swings"]
            if len(touches) < 2 or touches[-1].index < len(frame) - 252:
                continue
            lower, upper = cluster["lower"], cluster["upper"]
            broken = invalidated(cluster, len(frame) - 1)
            status = "broken" if broken else "confirmed"
            distance = (
                max(0.0, close - upper) / atr if kind == "L" else max(0.0, lower - close) / atr
            )
            output.append(
                {
                    "role": role,
                    "status": status,
                    "lower": lower,
                    "upper": upper,
                    "touches": len(touches),
                    "distance_atr": distance,
                    "confirmed_index": touches[-1].confirmed_index,
                    "established_index": cluster["established_index"],
                    "atr_at_establishment": cluster["atr_at_establishment"],
                    "touch_indices": [s.index for s in touches],
                }
            )
    return sorted(
        output, key=lambda z: (z["status"] != "confirmed", z["distance_atr"], -z["touches"])
    )


def formations(frame: pd.DataFrame, swings: list[Swing], indicators: pd.DataFrame) -> list[dict]:
    """Double bottom/top only after a close through the known neckline."""
    output: list[dict] = []
    for kind, name, direction in (
        ("L", "Double Bottom", "BULLISH"),
        ("H", "Double Top", "BEARISH"),
    ):
        pivots = [s for s in swings if s.kind == kind]
        for first, second in zip(pivots, pivots[1:], strict=False):
            atr = float(indicators.atr14.iloc[second.confirmed_index])
            if not np.isfinite(atr) or atr <= 0 or not 5 <= second.index - first.index <= 60:
                continue
            if abs(first.price - second.price) > 0.75 * atr:
                continue
            necks = [
                s
                for s in swings
                if s.kind != kind
                and first.index < s.index < second.index
                and s.confirmed_index <= second.confirmed_index
            ]
            if not necks:
                continue
            neck = max(s.price for s in necks) if kind == "L" else min(s.price for s in necks)
            height = (
                neck - max(first.price, second.price)
                if kind == "L"
                else min(first.price, second.price) - neck
            )
            if height < 2 * atr:
                continue
            for i in range(second.confirmed_index, min(len(frame), second.confirmed_index + 41)):
                closes = frame.close.iloc[second.index + 1 : i + 1]
                invalid = (
                    (closes < min(first.price, second.price) - 0.5 * atr).any()
                    if kind == "L"
                    else (closes > max(first.price, second.price) + 0.5 * atr).any()
                )
                if invalid:
                    break
                previous, current = float(frame.close.iloc[i - 1]), float(frame.close.iloc[i])
                crossed = previous <= neck < current if kind == "L" else previous >= neck > current
                if crossed:
                    output.append(
                        {
                            "pattern": name,
                            "direction": direction,
                            "index": i,
                            "first_index": first.index,
                            "second_index": second.index,
                            "neckline": neck,
                            "atr_at_confirmation": atr,
                        }
                    )
                    break
    return sorted(output, key=lambda event: event["index"])


def divergences(swings: list[Swing], indicators: pd.DataFrame) -> list[dict]:
    output: list[dict] = []
    for kind, direction in (("L", "BULLISH"), ("H", "BEARISH")):
        pivots = [s for s in swings if s.kind == kind]
        for first, second in zip(pivots, pivots[1:], strict=False):
            if second.index - first.index > 60:
                continue
            a, b = (
                float(indicators.rsi14.iloc[first.index]),
                float(indicators.rsi14.iloc[second.index]),
            )
            if not np.isfinite(a + b):
                continue
            matches = (
                second.price < first.price and b >= a + 3
                if kind == "L"
                else second.price > first.price and b <= a - 3
            )
            if matches:
                output.append(
                    {
                        "direction": direction,
                        "index": second.confirmed_index,
                        "first_index": first.index,
                        "second_index": second.index,
                        "first_rsi": a,
                        "second_rsi": b,
                    }
                )
    return sorted(output, key=lambda event: event["index"])


def _number(value) -> float | None:
    return float(value) if isinstance(value, Real) and np.isfinite(value) else None


def analyze(
    frame: pd.DataFrame,
    *,
    symbol: str,
    source: str,
    currency: str,
    adjustment: str = "caller-provided OHLC, unadjusted unless stated",
) -> dict:
    validate(frame)
    if not all(isinstance(v, str) and v.strip() for v in (symbol, source, currency, adjustment)):
        raise ValueError("Symbol, source, currency and adjustment description required.")
    indicators = indicator_series(frame)
    if not np.isfinite(indicators.iloc[-1].drop(labels=["sma200"]).to_numpy()).all():
        raise ValueError("Indicator calculation produced invalid values.")
    atr = float(indicators.atr14.iloc[-1])
    close = float(frame.close.iloc[-1])
    swings = confirmed_swings(frame)
    breaks, bias = structure_breaks(frame, swings)
    zones = price_zones(frame, swings, indicators.atr14)
    patterns = formations(frame, swings, indicators)
    divs = divergences(swings, indicators)
    trends = []
    for window in (20, 50, 200):
        if len(frame) <= window or pd.isna(indicators[f"sma{window}"].iloc[-6]):
            trends.append({"window": window, "direction": "UNAVAILABLE", "efficiency": None})
            continue
        net = float(frame.close.iloc[-1] - frame.close.iloc[-window - 1])
        path = float(frame.close.iloc[-window - 1 :].diff().abs().sum())
        slope = float(indicators[f"sma{window}"].iloc[-1] - indicators[f"sma{window}"].iloc[-6])
        ma = float(indicators[f"sma{window}"].iloc[-1])
        direction = (
            "BULLISH"
            if close > ma and slope > 0
            else "BEARISH"
            if close < ma and slope < 0
            else "NEUTRAL"
        )
        trends.append(
            {
                "window": window,
                "direction": direction,
                "sma": ma,
                "five_bar_slope": slope,
                "efficiency": abs(net) / path if path else 0.0,
                "distance_atr": (close - ma) / atr if atr > 0 else None,
            }
        )
    known = [t["direction"] for t in trends if t["direction"] != "UNAVAILABLE"]
    trend_vote = (
        "BULLISH"
        if known.count("BULLISH") > len(known) / 2
        else "BEARISH"
        if known.count("BEARISH") > len(known) / 2
        else "NEUTRAL"
    )
    hist = float(indicators.macd_hist.iloc[-1])
    momentum = "BULLISH" if hist > 0 else "BEARISH" if hist < 0 else "NEUTRAL"
    votes = {"trend": trend_vote, "structure": bias, "momentum": momentum}
    state = (
        "BULLISH"
        if list(votes.values()).count("BULLISH") >= 2
        else "BEARISH"
        if list(votes.values()).count("BEARISH") >= 2
        else "NEUTRAL"
    )
    reasons = [f"{key}: {value}" for key, value in votes.items()]
    conflicts = []
    if "BULLISH" in votes.values() and "BEARISH" in votes.values():
        conflicts.append("Trend, close-confirmed structure and MACD momentum disagree.")
    near_support = next(
        (
            z
            for z in zones
            if z["role"] == "support" and z["status"] == "confirmed" and z["distance_atr"] <= 1
        ),
        None,
    )
    if near_support:
        reasons.append(
            "Confirmed support is within 1 ATR; this is price location, not reversal confirmation."
        )
        if state == "BEARISH":
            conflicts.append(
                "Technical state remains BEARISH near support; proximity alone does not reverse the trend."
            )
    rsi = float(indicators.rsi14.iloc[-1])
    if rsi < 30 or rsi > 70:
        reasons.append("RSI is oversold." if rsi < 30 else "RSI is overbought.")
        if state == "BEARISH" and rsi < 30:
            conflicts.append(
                "Oversold RSI can persist in a downtrend; no confirmed reversal follows from RSI alone."
            )
    if len(frame) < 205:
        conflicts.append(
            "200-session trend needs 205 bars including its five-bar slope; unavailable windows do not vote."
        )

    def dated(event):
        return {**event, "date": frame.index[event["index"]].date().isoformat()}

    series = []
    start = max(0, len(frame) - 252)
    for i in range(start, len(frame)):
        series.append(
            {
                "date": frame.index[i].date().isoformat(),
                "close": float(frame.close.iloc[i]),
                **{key: _number(value) for key, value in indicators.iloc[i].items()},
            }
        )
    return {
        "schema_version": 1,
        "mode": "DESCRIPTIVE_READ_ONLY",
        "symbol": symbol,
        "source": source,
        "currency": currency,
        "adjustment": adjustment,
        "as_of": frame.index[-1].date().isoformat(),
        "bars": len(frame),
        "assessment": {"state": state, "reasons": reasons, "conflicts": conflicts, "votes": votes},
        "trends": trends,
        "momentum": {
            "rsi14": rsi,
            "rsi_state": "OVERBOUGHT" if rsi > 70 else "OVERSOLD" if rsi < 30 else "NEUTRAL",
            "macd": float(indicators.macd.iloc[-1]),
            "signal": float(indicators.macd_signal.iloc[-1]),
            "histogram": hist,
        },
        "atr14": atr,
        "structure_bias": bias,
        "swings": [
            {
                **asdict(s),
                "date": frame.index[s.index].date().isoformat(),
                "confirmed_at": frame.index[s.confirmed_index].date().isoformat(),
            }
            for s in swings
        ],
        "breaks": [dated(e) for e in breaks],
        "zones": [
            {
                **z,
                "confirmed_at": frame.index[z["confirmed_index"]].date().isoformat(),
                "established_at": frame.index[z["established_index"]].date().isoformat(),
            }
            for z in zones
        ],
        "patterns": [dated(e) for e in patterns],
        "divergences": [dated(e) for e in divs],
        "series": series,
        "limits": [
            "Strict pivots need three later completed bars; dates separate origin and availability.",
            "A BOS/CHoCH is a close-confirmed level break, not a forecast. Initial BOS establishes direction.",
            "Unconfirmed pivots, single-touch zones and pattern candidates are excluded.",
            "Daily bars must be completed sessions supplied by the caller; calendar/completeness is not independently verified.",
            "No forecast accuracy or profitable trading rule has been established.",
        ],
    }
