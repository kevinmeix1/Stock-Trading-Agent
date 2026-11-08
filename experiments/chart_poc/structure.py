"""Causal confirmed fractals and Double Bottom v1; closed daily bars only."""

from __future__ import annotations

import numpy as np


def atr(ohlc: np.ndarray, period: int = 14) -> np.ndarray:
    out = np.full(len(ohlc), np.nan)
    if len(ohlc) < period:
        return out
    high, low, close = ohlc[:, 1], ohlc[:, 2], ohlc[:, 3]
    tr = high - low
    tr[1:] = np.maximum(tr[1:], np.maximum(abs(high[1:] - close[:-1]), abs(low[1:] - close[:-1])))
    out[period - 1] = np.mean(tr[:period])
    for i in range(period, len(ohlc)):
        out[i] = (out[i - 1] * (period - 1) + tr[i]) / period
    return out


def detect(ohlc: np.ndarray, cfg: dict) -> dict:
    radius = cfg["pivot_radius"]
    volatility = atr(ohlc)
    swings, patterns, pending = [], [], []
    previous = {}
    for now in range(2 * radius, len(ohlc)):
        center = now - radius
        section = ohlc[center - radius : now + 1]
        kinds = []
        if np.argmin(section[:, 2]) == radius:
            kinds.append(("L", float(ohlc[center, 2])))
        if np.argmax(section[:, 1]) == radius:
            kinds.append(("H", float(ohlc[center, 1])))
        # Outside bar can satisfy both. Drop the ambiguous pivot, not invent order.
        if len(kinds) == 1:
            kind, price = kinds[0]
            prior = previous.get(kind)
            label = (
                kind
                if prior is None
                else (
                    ("HH" if price > prior else "LH" if price < prior else "EH")
                    if kind == "H"
                    else ("HL" if price > prior else "LL" if price < prior else "EL")
                )
            )
            event = {
                "kind": kind,
                "label": label,
                "pivot": center,
                "confirmed_at": now,
                "price": price,
            }
            swings.append(event)
            previous[kind] = price
            if (
                len(swings) >= 3
                and [x["kind"] for x in swings[-3:]] == ["L", "H", "L"]
                and np.isfinite(volatility[now])
            ):
                first, neck, second = swings[-3:]
                scale = float(volatility[now])
                gap = second["pivot"] - first["pivot"]
                if (
                    cfg["double_bottom_min_gap"] <= gap <= cfg["double_bottom_max_gap"]
                    and abs(second["price"] - first["price"]) <= cfg["bottom_tolerance_atr"] * scale
                    and neck["price"] - max(first["price"], second["price"])
                    >= cfg["min_rebound_atr"] * scale
                ):
                    pending.append(
                        {
                            "first_bottom": first["pivot"],
                            "second_bottom": second["pivot"],
                            "neck_pivot": neck["pivot"],
                            "neckline": neck["price"],
                            "floor": min(first["price"], second["price"]),
                            "created_at": now,
                            "formation_atr": scale,
                        }
                    )
        remaining = []
        for candidate in pending:
            if now - candidate["second_bottom"] > cfg["expiry_bars"]:
                continue
            if (
                ohlc[now, 3]
                < candidate["floor"] - cfg["invalidation_atr"] * candidate["formation_atr"]
            ):
                continue
            if (
                ohlc[now, 3]
                > candidate["neckline"] + cfg["break_buffer_atr"] * candidate["formation_atr"]
            ):
                patterns.append({**candidate, "confirmed_at": now, "close": float(ohlc[now, 3])})
            else:
                remaining.append(candidate)
        pending = remaining
    return {"swings": swings, "double_bottoms": patterns}
