"""Deterministic structure/indicator/time-availability and report regressions."""

from __future__ import annotations

import json
import subprocess
import sys

import numpy as np
import pandas as pd
import pytest

from .__main__ import html_report, load_csv
from .engine import (
    Swing,
    analyze,
    confirmed_swings,
    divergences,
    formations,
    indicator_series,
    price_zones,
    structure_breaks,
)


def bars(prices):
    prices = np.asarray(prices, dtype=float)
    return pd.DataFrame(
        {
            "open": prices,
            "high": prices + 0.2,
            "low": prices - 0.2,
            "close": prices,
            "volume": 1000.0,
        },
        index=pd.bdate_range("2024-01-01", periods=len(prices)),
    )


def chart(anchors, length=80):
    return bars(np.interp(np.arange(length), list(anchors), list(anchors.values())))


def report(frame):
    return analyze(frame, symbol="TEST", source="synthetic test fixture", currency="USD")


@pytest.mark.parametrize(
    "prices,rsi",
    [(np.arange(1, 101), 100.0), (np.arange(100, 0, -1), 0.0), (np.ones(100) * 10, 50.0)],
)
def test_wilder_rsi_edges_and_seed(prices, rsi):
    values = indicator_series(bars(prices)).rsi14
    assert values.iloc[:14].isna().all()
    assert (values.iloc[14:] == rsi).all()


def test_rsi_and_atr_hand_calculated():
    frame = bars(
        np.array(
            [
                10.0,
                11.0,
                10.0,
                11.0,
                10.0,
                11.0,
                10.0,
                11.0,
                10.0,
                11.0,
                10.0,
                11.0,
                10.0,
                11.0,
                12.0,
                11.0,
            ]
        )
    )
    indicators = indicator_series(frame)
    assert indicators.rsi14.iloc[14] == pytest.approx(100 * 8 / 14)
    assert indicators.rsi14.iloc[15] == pytest.approx(100 * (8 * 13 / 14) / 14)
    assert indicators.atr14.iloc[13] == pytest.approx((0.4 + 13 * 1.2) / 14)


def test_exact_confirmed_swing_sequence_and_confirmation_lag():
    frame = chart({0: 10, 5: 15, 10: 9, 15: 17, 20: 11, 25: 16, 30: 8, 35: 18, 40: 12, 79: 20})
    swings = confirmed_swings(frame)
    assert [(s.index, s.label) for s in swings[:6]] == [
        (5, "H"),
        (10, "L"),
        (15, "HH"),
        (20, "HL"),
        (25, "LH"),
        (30, "LL"),
    ]
    assert all(s.confirmed_index == s.index + 3 for s in swings)
    assert not any(s.index == 30 for s in confirmed_swings(frame.iloc[:33]))
    assert any(s.index == 30 for s in confirmed_swings(frame.iloc[:34]))


def test_equal_plateau_is_not_a_strict_swing():
    frame = bars([10, 11, 12, 13, 13, 12, 11, 10, 9, 8])
    assert not any(s.kind == "H" for s in confirmed_swings(frame))


def test_close_break_required_wick_is_insufficient_and_no_repeat():
    frame = bars([10, 10, 11, 12, 11, 10, 10, 12, 12, 12, 11])
    swing = Swing(3, 6, "H", 12.2, "H")
    frame.loc[frame.index[7], "high"] = 14
    assert structure_breaks(frame, [swing])[0] == []
    frame.loc[frame.index[8], ["open", "high", "close"]] = [13, 13.2, 13]
    events, bias = structure_breaks(frame, [swing])
    assert len(events) == 1 and events[0]["index"] == 8 and events[0]["event"] == "BOS"
    assert bias == "BULLISH"


def test_choch_needs_opposite_preceding_break():
    frame = bars([10, 10, 11, 12, 11, 10, 10, 13, 10, 7, 7])
    events, _ = structure_breaks(frame, [Swing(3, 6, "H", 12.2, "H"), Swing(5, 8, "L", 9.8, "L")])
    assert [(e["event"], e["direction"]) for e in events] == [
        ("BOS", "BULLISH"),
        ("CHoCH", "BEARISH"),
    ]


def test_zones_need_two_touches_and_breaks_remove_active_support():
    frame = bars(np.full(80, 10.4))
    swings = [Swing(20, 23, "L", 10.0, "L"), Swing(40, 43, "L", 10.1, "HL")]
    atr = pd.Series(np.ones(len(frame)))
    assert price_zones(frame, swings[:1], atr) == []
    zone = price_zones(frame, swings, atr)[0]
    assert (
        zone["status"] == "confirmed"
        and zone["touches"] == 2
        and zone["distance_atr"] == pytest.approx(0.05)
    )
    frame.loc[frame.index[60], ["open", "low", "high", "close"]] = [9.0, 8.8, 9.2, 9.0]
    assert price_zones(frame, swings, atr)[0]["status"] == "broken"


def test_future_volatility_cannot_rewrite_established_zone_geometry():
    frame = bars(np.full(80, 10.4))
    frame.loc[frame.index[20], "low"] = 10.0
    frame.loc[frame.index[40], "low"] = 10.1
    original = report(frame)["zones"][0]
    future = bars(np.full(100, 10.4))
    future.iloc[:80] = frame.to_numpy()
    future.loc[future.index[80:], "high"] = 20.0
    future.loc[future.index[80:], "low"] = 1.0
    extended = report(future)["zones"][0]
    for key in ("lower", "upper", "confirmed_at", "established_index", "established_at"):
        assert original[key] == extended[key]


def test_zone_candidates_reset_after_a_break_between_touches():
    frame = bars(np.full(80, 100.4))
    frame.loc[frame.index[30], ["open", "high", "low", "close"]] = [90.0, 90.2, 89.8, 90.0]
    swings = [Swing(20, 23, "L", 100.0, "L"), Swing(40, 43, "L", 100.1, "HL")]
    assert price_zones(frame, swings, pd.Series(np.ones(80))) == []


@pytest.mark.parametrize(
    "kind,name,first,second,neck,prices",
    [
        ("L", "Double Bottom", 10.0, 10.2, 14.0, [12.0, 13.0, 14.0, 15.0, 16.0]),
        ("H", "Double Top", 14.0, 13.8, 10.0, [12.0, 11.0, 10.0, 9.0, 8.0]),
    ],
)
def test_pattern_needs_neckline_close_after_second_pivot_confirmation(
    kind, name, first, second, neck, prices
):
    frame = bars(np.full(80, 12.0))
    frame.loc[frame.index[43:48], ["open", "close"]] = np.repeat(
        np.array(prices)[:, None], 2, axis=1
    )
    frame.loc[frame.index[43:48], "high"] = np.array(prices) + 0.2
    frame.loc[frame.index[43:48], "low"] = np.array(prices) - 0.2
    swings = [
        Swing(20, 23, kind, first, kind),
        Swing(30, 33, "H" if kind == "L" else "L", neck, "H"),
        Swing(40, 43, kind, second, "HL"),
    ]
    indicators = pd.DataFrame({"atr14": np.ones(80)})
    assert formations(frame.iloc[:46], swings, indicators) == []
    output = formations(frame, swings, indicators)
    assert len(output) == 1 and output[0]["pattern"] == name and output[0]["index"] == 46


def test_divergence_requires_known_pivots_and_three_rsi_points():
    indicators = pd.DataFrame({"rsi14": np.full(100, 50.0)})
    indicators.loc[20, "rsi14"] = 24.0
    indicators.loc[40, "rsi14"] = 28.0
    swings = [Swing(20, 23, "L", 10.0, "L"), Swing(40, 43, "L", 9.0, "LL")]
    found = divergences(swings, indicators)
    assert len(found) == 1 and found[0]["direction"] == "BULLISH" and found[0]["index"] == 43
    indicators.loc[40, "rsi14"] = 26.0
    assert divergences(swings, indicators) == []


def test_future_bars_cannot_change_known_events_or_indicators():
    rng = np.random.default_rng(8)
    frame = bars(100 + np.cumsum(rng.normal(0, 1, 320)))
    cutoff = 220
    prefix = report(frame.iloc[:cutoff])
    mutated = frame.copy()
    mutated.iloc[cutoff:, mutated.columns.get_indexer(["open", "high", "low", "close"])] += 200
    full = report(mutated)
    assert [s for s in full["swings"] if s["confirmed_index"] < cutoff] == prefix["swings"]
    for key in ("breaks", "patterns", "divergences"):
        assert [e for e in full[key] if e["index"] < cutoff] == prefix[key]
    pd.testing.assert_frame_equal(
        indicator_series(frame.iloc[:cutoff]), indicator_series(mutated).iloc[:cutoff]
    )


def test_bearish_state_near_support_stays_bearish():
    # Downtrend with two previously confirmed lows near the latest close.
    frame = chart(
        {
            0: 150,
            40: 140,
            80: 135,
            120: 125,
            160: 110,
            180: 100,
            190: 108,
            200: 100.1,
            210: 106,
            230: 100.4,
        },
        231,
    )
    result = report(frame)
    assert result["assessment"]["state"] == "BEARISH"
    assert any(
        z["role"] == "support" and z["status"] == "confirmed" and z["distance_atr"] <= 1
        for z in result["zones"]
    )
    assert any("remains BEARISH near support" in s for s in result["assessment"]["conflicts"])


def test_oversold_is_not_itself_a_bullish_vote():
    result = report(bars(np.linspace(150, 50, 260)))
    assert result["momentum"]["rsi14"] == 0
    assert result["assessment"]["state"] == "BEARISH"
    assert "forecast" not in result and "decision" not in result


def test_short_history_marks_200_day_window_unavailable():
    result = report(bars(np.linspace(50, 100, 70)))
    assert result["trends"][-1]["direction"] == "UNAVAILABLE"
    assert result["series"][-1]["sma200"] is None


@pytest.mark.parametrize(
    "kind",
    ["nan", "inf", "negative", "badbar", "duplicate", "short", "unordered", "negativevolume"],
)
def test_invalid_input_rejected(kind):
    frame = bars(np.linspace(50, 100, 100))
    if kind in {"nan", "inf", "negative"}:
        frame.iloc[-1, frame.columns.get_loc("close")] = {
            "nan": np.nan,
            "inf": np.inf,
            "negative": -1,
        }[kind]
    elif kind == "badbar":
        frame.iloc[-1, frame.columns.get_loc("high")] = 1.0
    elif kind == "duplicate":
        frame = pd.concat([frame, frame.iloc[-1:]])
    elif kind == "short":
        frame = frame.iloc[:49]
    elif kind == "unordered":
        frame = frame.iloc[::-1]
    else:
        frame.iloc[-1, frame.columns.get_loc("volume")] = -1.0
    with pytest.raises(ValueError):
        report(frame)


def test_load_checksum_adjustment_and_injection_safe_html(tmp_path):
    frame = bars(np.linspace(50, 100, 100))
    frame["adj_close"] = frame.close * 0.5
    path = tmp_path / "source.csv"
    frame.rename_axis("date").to_csv(path)
    with pytest.raises(ValueError, match="SHA-256"):
        load_csv(path, expected_sha256="0" * 64)
    adjusted, digest = load_csv(path, adjusted=True)
    assert adjusted.close.iloc[-1] == 50.0
    result = analyze(
        adjusted, symbol="</script><script>bad()</script>", source="fixture", currency="USD"
    )
    html = html_report(result)
    assert "</script><script>bad()" not in html
    assert "\\u003c/script>" in html and len(digest) == 64
    json.dumps(result, allow_nan=False)


def test_cli_cutoff_is_before_analysis_and_output_is_reproducible(tmp_path):
    frame = bars(np.linspace(50, 100, 260))
    path = tmp_path / "source.csv"
    frame.rename_axis("date").to_csv(path)
    cutoff = frame.index[219].date().isoformat()
    command = [
        sys.executable,
        "-m",
        "experiments.structure_desk",
        "--csv",
        str(path),
        "--symbol",
        "TEST",
        "--source",
        "synthetic fixture",
        "--currency",
        "USD",
        "--as-of",
        cutoff,
    ]
    for name in ("one", "two"):
        subprocess.run(
            [*command, "--output", str(tmp_path / name)], check=True, capture_output=True, text=True
        )
    first = (tmp_path / "one/report.json").read_bytes()
    assert first == (tmp_path / "two/report.json").read_bytes()
    assert (tmp_path / "one/index.html").read_bytes() == (tmp_path / "two/index.html").read_bytes()
    assert json.loads(first)["as_of"] == cutoff
    assert json.loads(first)["bars"] == 220
