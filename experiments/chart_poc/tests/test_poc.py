from __future__ import annotations

import ast
import hashlib
import json
import shutil

import numpy as np
import pytest
import stumpy

from experiments.chart_poc.data import Series, load_data
from experiments.chart_poc.matching import Predictor, select_neighbors
from experiments.chart_poc.structure import atr, detect
from experiments.chart_poc.study import HERE, accuracy, evaluate, paired_interval, summarize

CFG = json.loads((HERE / "protocol.json").read_text(encoding="utf-8"))


def fixture():
    close = np.array(
        [12, 11, 10, 11, 12, 13, 14, 15, 14, 13, 12, 11, 10.3, 11, 12, 13, 14, 16, 17, 16],
        dtype=float,
    )
    return np.column_stack((close, close + 0.2, close - 0.2, close))


def test_real_snapshot_and_adjustments():
    data, manifest = load_data(HERE / "data")
    assert len(manifest["symbols"]) == 3
    for s in data.values():
        assert len(s.close) == 3270
        assert not s.ohlc.flags.writeable
        assert s.dates[0] == "2000-03-01"
        assert s.dates[-1] == "2013-03-01"
        assert np.all(s.ohlc[:, 1] >= s.close)
        assert np.all(s.ohlc[:, 2] <= s.close)


def test_snapshot_tamper_fails_closed(tmp_path):
    shutil.copytree(HERE / "data", tmp_path / "data")
    path = tmp_path / "data" / "AAPL.csv"
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="checksum"):
        load_data(tmp_path / "data")


def test_invalid_ohlc_is_rejected_even_with_matching_hash(tmp_path):
    shutil.copytree(HERE / "data", tmp_path / "data")
    path = tmp_path / "data" / "AAPL.csv"
    lines = path.read_text().splitlines()
    row = lines[1].split(",")
    row[2] = "0.1"
    lines[1] = ",".join(row)
    raw = ("\n".join(lines) + "\n").encode()
    path.write_bytes(raw)
    manifest = json.loads((tmp_path / "data" / "manifest.json").read_text())
    manifest["symbols"][0]["sha256"] = hashlib.sha256(raw).hexdigest()
    (tmp_path / "data" / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="geometry"):
        load_data(tmp_path / "data")


def test_atr_golden_and_prefix():
    bars = np.tile([10.0, 11.0, 9.0, 10.0], (30, 1))
    values = atr(bars)
    assert np.isnan(values[:13]).all()
    np.testing.assert_allclose(values[13:], 2.0)
    np.testing.assert_equal(values[:20], atr(bars[:20]))


@pytest.mark.parametrize("scale,offset", [(1, 0), (3, 0), (1, 100), (0.1, 0)])
def test_double_bottom_known_geometry_and_scale_invariance(scale, offset):
    bars = fixture() * scale + offset
    result = detect(bars, CFG["structures"])
    assert len(result["double_bottoms"]) == 1
    pattern = result["double_bottoms"][0]
    assert (
        pattern["first_bottom"],
        pattern["second_bottom"],
        pattern["created_at"],
        pattern["confirmed_at"],
    ) == (2, 12, 14, 17)
    assert [x["label"] for x in result["swings"]] == ["L", "H", "HL"]


def test_structure_all_prefixes_and_future_mutation():
    bars = fixture()
    full = detect(bars, CFG["structures"])
    for end in range(5, len(bars) + 1):
        prefix = detect(bars[:end], CFG["structures"])
        for key in full:
            assert prefix[key] == [x for x in full[key] if x["confirmed_at"] < end]
    changed = np.vstack((bars, np.tile([1.0, 100.0, 0.5, 1.0], (10, 1))))
    later = detect(changed, CFG["structures"])
    for key in full:
        assert full[key] == [x for x in later[key] if x["confirmed_at"] < len(bars)]


def test_no_break_no_confirmed_pattern():
    assert not detect(fixture()[:17], CFG["structures"])["double_bottoms"]


def test_bottom_too_deep_and_gap_too_short():
    bars = fixture()
    bars[12] = [6, 6.2, 5.8, 6]
    assert not detect(bars, CFG["structures"])["double_bottoms"]
    cfg = {**CFG["structures"], "double_bottom_min_gap": 11}
    assert not detect(fixture(), cfg)["double_bottoms"]


def test_failed_pending_pattern_invalidates_before_break():
    bars = fixture()
    bars[15] = [8.0, 8.2, 7.8, 8.0]
    assert not detect(bars, CFG["structures"])["double_bottoms"]


def test_pivot_confirmation_and_equal_extrema():
    bars = fixture()
    result = detect(bars, CFG["structures"])
    assert all(x["confirmed_at"] == x["pivot"] + 2 for x in result["swings"])
    flat = np.tile([10.0, 10.2, 9.8, 10.0], (40, 1))
    assert not detect(flat, CFG["structures"])["swings"]


def test_mass_equals_brute_force_z_distance():
    source = np.array([4.0, 8.0, 7.0, 3.0, 5.0, 2.0, 9.0, 11.0, 8.0, 4.0])
    query = np.array([1.0, 3.0, 2.0, 0.0])
    actual = stumpy.mass(query, source)

    def normalized(x):
        return (x - np.mean(x)) / np.std(x)

    expected = [np.linalg.norm(normalized(query) - normalized(source[i : i + 4])) for i in range(7)]
    np.testing.assert_allclose(actual, expected, atol=1e-7)


def test_historical_neighbors_disjoint_and_complete_outcomes():
    x = np.arange(1000)
    library = np.log(100 + x * 0.1 + 3 * np.sin(x / 7))
    query = library[-60:]
    matches = select_neighbors(library, query, 20, 5)
    for i, a in enumerate(matches):
        assert a["outcome_end"] < len(library)
        for b in matches[i + 1 :]:
            assert a["outcome_end"] < b["start"] or b["outcome_end"] < a["start"]


def test_constant_query_is_not_a_match():
    with pytest.raises(ValueError, match="constant"):
        select_neighbors(np.arange(100, dtype=float), np.ones(5), 2, 2)


def test_predictor_past_only_and_baseline_definitions():
    x = np.arange(1100)
    close = 100 + 0.1 * x + 3 * np.sin(x / 7)
    predictor = Predictor(close[:1000], 60, 20, 5)
    before = predictor.predict(close[:1050])
    mutated = close.copy()
    mutated[1050:] *= 10
    assert before == predictor.predict(mutated[:1050])
    assert before["trend"] == int(np.sign(close[1030:1050].mean() - close[1000:1050].mean()))
    assert before["momentum"] == int(np.sign(close[1049] / close[1029] - 1))
    assert all(m["outcome_end"] < 990 for m in before["matches"])


def test_evaluator_forecasts_unchanged_after_target_mutation():
    series, _ = load_data(HERE / "data")
    s = series["AAPL"]
    cfg = {**CFG, "symbols": ["AAPL"], "validation_end": "2007-03-01", "holdout_end": "2010-03-01"}
    original, _ = evaluate({"AAPL": s}, cfg)
    cutoff = original[-1]["index"]
    changed = s.close.copy()
    changed[cutoff + 1 :] *= 0.5
    altered, _ = evaluate({"AAPL": Series(s.symbol, s.dates, s.ohlc, changed)}, cfg)
    for a, b in zip(original, altered, strict=True):
        assert a["matches"] == b["matches"]
        assert a["mass"] == b["mass"]
        assert a["trend"] == b["trend"]
        assert a["momentum"] == b["momentum"]
    assert original[-1]["actual_log_return"] != altered[-1]["actual_log_return"]
    assert all(r["close_path_mae"] <= 0 <= r["close_path_mfe"] for r in original)


def test_paired_bootstrap_known_result_and_reproducibility():
    x = np.ones(30) * 0.25
    assert paired_interval(x, 5, 200, 42, 0.975) == [0.25, 0.25]
    assert paired_interval(np.arange(30) / 30, 5, 200, 42, 0.975) == paired_interval(
        np.arange(30) / 30, 5, 200, 42, 0.975
    )


def test_accuracy_and_pairing_validation():
    assert accuracy(1, 0.1) == 1
    assert accuracy(-1, 0.1) == 0
    assert accuracy(0, 0.1) == 0.5
    with pytest.raises(ValueError, match="Empty"):
        summarize([], CFG)


def test_exact_hh_hl_lh_ll_and_equal_labels():
    close = np.array(
        [
            10,
            11,
            12,
            13,
            12,
            11,
            10,
            9,
            10,
            11,
            12,
            14,
            13,
            12,
            11,
            10,
            11,
            12,
            11,
            10,
            9,
            8,
            9,
            10,
            11,
            12,
            11,
            10,
            9,
            8,
            9,
            10,
        ],
        dtype=float,
    )
    bars = np.column_stack((close, close + 0.2, close - 0.2, close))
    result = detect(bars, CFG["structures"])
    assert [(x["pivot"], x["label"]) for x in result["swings"]] == [
        (3, "H"),
        (7, "L"),
        (11, "HH"),
        (15, "HL"),
        (17, "LH"),
        (21, "LL"),
        (25, "EH"),
        (29, "EL"),
    ]


def test_outside_bar_does_not_invent_pivot_order():
    bars = np.tile([10.0, 10.2, 9.8, 10.0], (7, 1))
    bars[3] = [10.0, 20.0, 1.0, 10.0]
    assert not detect(bars, CFG["structures"])["swings"]


def test_equal_bottom_plateau_uses_first_available_extreme():
    close = np.array([12, 11, 10, 10, 11, 12], dtype=float)
    bars = np.column_stack((close, close + 0.2, close - 0.2, close))
    result = detect(bars, CFG["structures"])
    assert [(x["pivot"], x["label"]) for x in result["swings"]] == [(2, "L")]


def test_complete_study_reproduces_committed_artifacts(tmp_path):
    from experiments.chart_poc.study import run

    run(tmp_path)
    for name in (
        "summary.json",
        "predictions.json",
        "predictions.csv",
        "structures.json",
        "REPORT.md",
    ):
        assert (tmp_path / name).read_bytes() == (HERE / "results" / name).read_bytes(), name


def test_no_application_or_network_import_in_analysis():
    for path in HERE.glob("*.py"):
        if path.name == "freeze_data.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        names = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.extend(x.name for x in node.names)
            elif isinstance(node, ast.ImportFrom):
                names.append(node.module or "")
        assert not any(
            name.startswith(("stock_trading_agent", "urllib", "requests", "httpx"))
            for name in names
        ), path


def test_predictor_invariant_to_common_positive_price_scaling():
    x = np.arange(1100)
    close = 100 + 0.1 * x + 3 * np.sin(x / 7)
    first = Predictor(close[:1000], 60, 20, 5).predict(close)
    second = Predictor(close[:1000] * 10, 60, 20, 5).predict(close * 10)
    for key in ("mass", "trend", "momentum", "always_positive"):
        assert first[key] == second[key]
    assert [m["start"] for m in first["matches"]] == [m["start"] for m in second["matches"]]
    np.testing.assert_allclose(
        [m["distance"] for m in first["matches"]],
        [m["distance"] for m in second["matches"]],
        atol=1e-7,
    )
