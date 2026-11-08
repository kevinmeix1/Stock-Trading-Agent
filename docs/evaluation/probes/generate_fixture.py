"""Synthetic computational comparison only; no market performance test."""

import importlib.util
import json
import math
from pathlib import Path

root = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("atila_indicators", root / "atila-indicators.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
bars = []

for i in range(320):
    close = 100 + i * 0.04 + 4 * math.sin(i / 9) + 1.5 * math.cos(i / 3)
    bars.append(
        dict(
            time=1700000000 + i * 86400,
            open=close - 0.3,
            high=close + 1.2 + (i % 7) * 0.1,
            low=close - 1.1 - (i % 5) * 0.08,
            close=close,
            volume=1000 + i % 17 * 13,
        )
    )
closes = [b["close"] for b in bars]
result = {
    "fixture": "SIMULATED_320_OHLCV_BARS",
    "bars": bars,
    "sma20": module.calc_sma(closes, 20),
    "ema20": module.calc_ema(closes, 20),
    "rsi14": module.calc_rsi(closes, 14),
    "atr14": module.calc_atr([b["high"] for b in bars], [b["low"] for b in bars], closes, 14),
}
(root / "fixture-comparison.json").write_text(json.dumps(result, allow_nan=False), encoding="utf-8")
print("Synthetic fixture and Python reference arrays generated: 320 bars")
