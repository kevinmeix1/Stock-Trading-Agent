"""Offline paired forecast evaluation, not a trading/execution backtest."""

from __future__ import annotations

import csv
import hashlib
import importlib.metadata
import json
from pathlib import Path

import numpy as np

from .data import load_data
from .matching import Predictor
from .structure import detect

HERE = Path(__file__).resolve().parent


def digest(value) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def accuracy(prediction: int, actual: float) -> float:
    return 0.5 if prediction == 0 or actual == 0 else float(prediction == np.sign(actual))


def paired_interval(
    differences: np.ndarray, block: int, replicates: int, seed: int, level: float
) -> list:
    values = np.asarray(differences, dtype=float)
    n = len(values)
    if n < 2 * block:
        raise ValueError("Insufficient query dates for this block bootstrap")
    rng = np.random.default_rng(seed)
    starts = rng.integers(0, n - block + 1, size=(replicates, int(np.ceil(n / block))))
    index = (starts[:, :, None] + np.arange(block)).reshape(replicates, -1)[:, :n]
    means = np.mean(values[index], axis=1)
    tail = (1 - level) / 2
    return [float(x) for x in np.quantile(means, [tail, 1 - tail])]


def summarize(records: list[dict], cfg: dict) -> dict:
    output = {}
    for phase in ("validation", "holdout"):
        rows = [x for x in records if x["phase"] == phase]
        if not rows:
            raise ValueError("Empty evaluation phase")
        by_date = {}
        for row in rows:
            by_date.setdefault(row["date"], []).append(row)
        dates = sorted(by_date)
        if any(len(by_date[d]) != 3 for d in dates):
            raise ValueError("Unpaired symbol/date sample")
        methods = ("mass", "trend", "momentum", "always_positive")
        scores = {
            m: float(np.mean([accuracy(x[m], x["actual_log_return"]) for x in rows]))
            for m in methods
        }
        comparisons = {}
        b = cfg["bootstrap"]
        for baseline in ("trend", "momentum"):
            # Cross-stock observations are averaged on each common date before
            # resampling contiguous date blocks, preserving common market shocks.
            differences = np.array(
                [
                    np.mean(
                        [
                            accuracy(x["mass"], x["actual_log_return"])
                            - accuracy(x[baseline], x["actual_log_return"])
                            for x in by_date[d]
                        ]
                    )
                    for d in dates
                ]
            )
            comparisons[baseline] = {
                "difference": float(np.mean(differences)),
                "interval": paired_interval(
                    differences,
                    b["block_length_query_dates"],
                    b["replicates"],
                    b["seed"],
                    b["interval_per_comparison"],
                ),
                "sensitivity": {
                    str(length): paired_interval(
                        differences,
                        length,
                        b["replicates"],
                        b["seed"],
                        b["interval_per_comparison"],
                    )
                    for length in b["sensitivity_blocks"]
                },
            }
        per_symbol = {
            s: {
                m: float(
                    np.mean(
                        [accuracy(x[m], x["actual_log_return"]) for x in rows if x["symbol"] == s]
                    )
                )
                for m in methods
            }
            for s in cfg["symbols"]
        }
        output[phase] = {
            "observations": len(rows),
            "query_dates": len(dates),
            "from": dates[0],
            "to": dates[-1],
            "accuracy": scores,
            "per_symbol": per_symbol,
            "comparisons": comparisons,
            "within_sample_evidence": all(v["interval"][0] > 0 for v in comparisons.values()),
        }
    return output


def evaluate(series: dict, cfg: dict) -> tuple[list, dict]:
    records = []
    structure = {}
    for symbol in cfg["symbols"]:
        s = series[symbol]
        training_end = max(i for i, d in enumerate(s.dates) if d <= cfg["train_end"])
        predictor = Predictor(s.close[: training_end + 1], cfg["window"], cfg["horizon"], cfg["k"])
        events = detect(s.ohlc, cfg["structures"])
        pattern_rows = []
        for event in events["double_bottoms"]:
            t = event["confirmed_at"]
            h = cfg["horizon"]
            mature = t + h < len(s.close)
            outcome = None if not mature else float(np.log(s.close[t + h] / s.close[t]))
            failed = (
                None
                if not mature
                else bool(
                    np.any(
                        s.close[t + 1 : t + h + 1]
                        < event["floor"]
                        - cfg["structures"]["invalidation_atr"] * event["formation_atr"]
                    )
                )
            )
            pattern_rows.append(
                {
                    **event,
                    "date": s.dates[t],
                    "first_bottom_date": s.dates[event["first_bottom"]],
                    "second_bottom_date": s.dates[event["second_bottom"]],
                    "outcome": {
                        "mature": mature,
                        "log_return_20": outcome,
                        "close_invalidated_within_20": failed,
                    },
                }
            )
        swing_rows = [
            {
                **event,
                "pivot_date": s.dates[event["pivot"]],
                "confirmed_date": s.dates[event["confirmed_at"]],
            }
            for event in events["swings"]
        ]
        structure[symbol] = {"swings": swing_rows, "double_bottoms": pattern_rows}
        for phase in ("validation", "holdout"):
            start, end = cfg[phase + "_start"], cfg[phase + "_end"]
            first = next(i for i, d in enumerate(s.dates) if d >= start)
            last = max(i for i, d in enumerate(s.dates) if d <= end)
            for t in range(first, last - cfg["horizon"] + 1, cfg["stride"]):
                # Predictor receives only already closed prices. Outcomes are
                # read separately below, after the forecast has been constructed.
                prediction = predictor.predict(s.close[: t + 1])
                for match in prediction["matches"]:
                    match["start_date"] = s.dates[match["start"]]
                    match["end_date"] = s.dates[match["end"]]
                    match["outcome_end_date"] = s.dates[match["outcome_end"]]
                    if (
                        match["outcome_end"] >= t - cfg["window"] + 1
                        or match["outcome_end"] > training_end
                    ):
                        raise AssertionError("Historical match crosses query/training boundary")
                future = s.close[t + 1 : t + cfg["horizon"] + 1]
                records.append(
                    {
                        "symbol": symbol,
                        "phase": phase,
                        "date": s.dates[t],
                        "index": t,
                        "query_start": s.dates[t - cfg["window"] + 1],
                        "outcome_end": s.dates[t + cfg["horizon"]],
                        **prediction,
                        "actual_log_return": float(np.log(future[-1] / s.close[t])),
                        "close_path_mae": float(min(0.0, np.min(future / s.close[t] - 1))),
                        "close_path_mfe": float(max(0.0, np.max(future / s.close[t] - 1))),
                    }
                )
    return records, structure


def report_markdown(payload: dict) -> str:
    summary = payload["summary"]
    lines = [
        "# Chart-PoC: historischer Vergleichsbericht",
        "",
        "Reale eingefrorene Tagesdaten: AAPL, IBM und MSFT, 01.03.2000–01.03.2013. Historische Fallstudie, keine aktuelle Marktanalyse.",
        "",
        "## Ergebnis",
        "",
    ]
    evidence = summary["holdout"]["within_sample_evidence"]
    lines.append(
        "MASS zeigt innerhalb dieser Stichprobe einen positiven gepaarten Unterschied zu beiden Baselines."
        if evidence
        else "**Ein belastbarer Vorteil von MASS gegenüber beiden einfachen Trend-/Momentumverfahren ist in diesem Holdout nicht nachgewiesen.**"
    )
    lines += [
        "Drei korrelierte, überlebende US-Technologietitel erlauben keine belastbare allgemeine Aussage über andere Aktien, Sektoren oder heutige Märkte.",
        "",
        "| Phase | Prognosen / gemeinsame Termine | MASS | Trend SMA20/50 | Momentum20 | Immer positiv |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for phase, v in summary.items():
        a = v["accuracy"]
        lines.append(
            f"| {phase} | {v['observations']} / {v['query_dates']} | {a['mass']:.2%} | {a['trend']:.2%} | {a['momentum']:.2%} | {a['always_positive']:.2%} |"
        )
    lines += [
        "",
        "Primärmetrik: korrekte Richtung der tatsächlichen 20-Bar-Logrendite ab dem bekannten Schlusskurs. Neutral-/Nullfälle zählen 0,5. Das sind Prognosequoten, keine Handelsrenditen.",
        "",
        "## Gepaarte Holdout-Unterschiede",
        "",
        "| MASS minus | Unterschied in Prozentpunkten | Intervall |",
        "|---|---:|---|",
    ]
    for baseline, v in summary["holdout"]["comparisons"].items():
        lo, hi = v["interval"]
        lines.append(
            f"| {baseline} | {100 * v['difference']:+.2f} | [{100 * lo:+.2f}; {100 * hi:+.2f}] |"
        )
    lines += [
        "",
        "97,5%-Intervalle pro Vergleich, Bonferroni für zwei primäre Vergleiche; approximativer Moving-Block-Bootstrap über gemeinsame Termine, Blocklänge 5, 5.000 Wiederholungen, Seed 20261108. Aktien werden innerhalb jedes Datums gemeinsam gehalten. Rohprognosen sind keine unabhängigen Beobachtungen. Intervalle bedingen auf die fixe Trainingsbibliothek; sie erfassen keine Universums- oder Trainingsauswahlunsicherheit.",
        "",
        "## Einzelreihen im Holdout",
        "",
        "| Symbol | MASS | Trend | Momentum |",
        "|---|---:|---:|---:|",
    ]
    for symbol, v in summary["holdout"]["per_symbol"].items():
        lines.append(f"| {symbol} | {v['mass']:.2%} | {v['trend']:.2%} | {v['momentum']:.2%} |")
    lines += [
        "",
        "## Bestätigte Marktstrukturen und Double Bottoms",
        "",
        "Pivots werden erst zwei abgeschlossene Bars nach ihrem Extrem bekannt. HH/HL/LH/LL vergleichen aufeinanderfolgende bestätigte Extrema desselben Typs. Gleichstände erhalten EH/EL; Outside-Bar-Doppelpivots werden als mehrdeutig ausgelassen. Alle Ereignisse stehen in structures.json.",
        "",
        "| Symbol | Bestätigte Swings | Double Bottoms | Reife 20-Bar-Fälle | Davon negative Folge | Schlusskurs-Invalidierung binnen 20 Bars |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for symbol, s in payload["structures"].items():
        patterns = s["double_bottoms"]
        mature = [p for p in patterns if p["outcome"]["mature"]]
        lines.append(
            f"| {symbol} | {len(s['swings'])} | {len(patterns)} | {len(mature)} | {sum(p['outcome']['log_return_20'] < 0 for p in mature)} | {sum(p['outcome']['close_invalidated_within_20'] for p in mature)} |"
        )
    lines += [
        "",
        "Die Patternzählung umfasst den gesamten Datensatz einschließlich Training. Sie misst algorithmische Erkennung und beobachteten Verlauf, keine unabhängig annotierte Erkennungspräzision. Der MASS-Vergleich nutzt alle vorab geplanten Termine und ist nicht auf seltene Double Bottoms beschränkt.",
        "",
        "### Letzte drei bestätigte Swings je Reihe",
        "",
        "| Symbol | Pivotdatum | Erst bekannt am | Struktur | Preis in adjustierten Snapshot-USD |",
        "|---|---|---|---|---:|",
    ]
    for symbol, value in payload["structures"].items():
        for swing in value["swings"][-3:]:
            lines.append(
                f"| {symbol} | {swing['pivot_date']} | {swing['confirmed_date']} | {swing['label']} | {swing['price']:.4f} |"
            )
    lines += [
        "",
        "### Sämtliche bestätigten Double Bottoms und beobachtete Folge",
        "",
        "Die Preise sind rückwirkend adjustierte Snapshot-Einheiten, keine damaligen handelbaren Kurse. Negative Folgen bleiben aufgeführt.",
        "",
        "| Symbol | Erstes / zweites Tief | Close-Bestätigung | Nackenlinie adjustiert | Tatsächliche 20-Bar-Folge | Invalidierung binnen 20 Bars |",
        "|---|---|---|---:|---:|---|",
    ]
    for symbol, value in payload["structures"].items():
        for pattern in value["double_bottoms"]:
            outcome = pattern["outcome"]
            following = (
                f"{np.expm1(outcome['log_return_20']):+.2%}"
                if outcome["mature"]
                else "noch nicht verfügbar"
            )
            invalid = (
                ("ja" if outcome["close_invalidated_within_20"] else "nein")
                if outcome["mature"]
                else "offen"
            )
            lines.append(
                f"| {symbol} | {pattern['first_bottom_date']} / {pattern['second_bottom_date']} | {pattern['date']} | {pattern['neckline']:.4f} | {following} | {invalid} |"
            )
    lines += [
        "",
        "## Nachvollziehbare Fehlinterpretationen",
        "",
        "Auswahlregel: die drei größten absoluten Prognosefehler im Holdout, bei denen MASS eine positive Folge erwartet und die tatsächliche Folge negativ ist. Vollständige Treffer und Gegenbeispiele bleiben in predictions.json und predictions.csv enthalten.",
        "",
    ]
    failures = sorted(
        [
            r
            for r in payload["records"]
            if r["phase"] == "holdout" and r["mass"] > 0 and r["actual_log_return"] < 0
        ],
        key=lambda r: abs(r["mass_expected_log_return"] - r["actual_log_return"]),
        reverse=True,
    )[:3]
    if not failures:
        lines.append(
            "Kein Fall nach dieser Auswahlregel; daraus folgt keine allgemeine Fehlerfreiheit."
        )
    for r in failures:
        expected = np.expm1(r["mass_expected_log_return"])
        actual = np.expm1(r["actual_log_return"])
        lines += [
            f"### {r['symbol']} – {r['date']}",
            "",
            f"60-Bar-Query ab {r['query_start']}; erwarteter geometrischer 20-Bar-Verlauf {expected:+.2%}, tatsächlich bis {r['outcome_end']} {actual:+.2%}. Ähnliche Vergangenheit hat hier die Richtung verfehlt.",
            "",
            "| Historisches Fenster | Outcome bis | MASS-Distanz | Tatsächliche historische Folge |",
            "|---|---|---:|---:|",
        ]
        for m in r["matches"]:
            lines.append(
                f"| {m['start_date']}–{m['end_date']} | {m['outcome_end_date']} | {m['distance']:.4f} | {np.expm1(m['forward_log_return']):+.2%} |"
            )
        lines.append("")
    lines += [
        "## Methodik und Grenzen",
        "",
        "- Parameter wurden vor der ersten Ergebnisauswertung in protocol.json und einem eigenen Git-Commit fixiert; kein Tuning auf Validation oder Holdout.",
        "- Training endet 2006; Validation 2007–2009, Holdout 2010–2013. Alle fünf historischen Matches eines Queries stammen aus der festen Trainingsbibliothek, ihre vollständige 20-Bar-Folge endet zusätzlich vor Beginn des Queries. Feature- und Outcome-Intervalle der fünf Nachbarn überlappen sich nicht.",
        "- MASS vergleicht 60 logarithmierte Adjusted-Close-Werte mit Z-Normalisierung je Fenster (Populationsstandardabweichung, ddof=0). Kein DTW, keine Zeitdehnung, kein gelerntes Embedding. Formähnlichkeit beseitigt Preisniveau und Amplitude und garantiert keinen ähnlichen Folgepfad.",
        "- Trend: Vorzeichen SMA20 minus SMA50; Momentum: Vorzeichen der letzten 20-Bar-Rendite. Gleiche Query-/Outcome-Termine und dieselben verfügbaren 60 Bars. Immer-positiv kontrolliert den Markt-/Klassenbias.",
        "- 20-Bar-Abstand verhindert sich überlappende Zielrenditeintervalle; die 60-Bar-Features bleiben überlappend. Die Blocklängen 3 und 8 werden unverändert als Sensitivität in summary.json ausgewiesen.",
        "- Snapshot-OHLC werden mit adj_close/close skaliert. Dies ist eine rückwirkend adjustierte Quelle einschließlich späterer Kapitalmaßnahmen, kein historischer Point-in-time-Feed. Z-normalisierte Preisformen und ATR-Verhältnisse sind invariant gegen einen gemeinsamen positiven Skalierungsfaktor; exakte damalige handelbare Preislevels werden nicht behauptet.",
        "- Keine unabhängigen menschlichen Patternlabels, keine Aussage über verpasste Formationen oder wissenschaftlich kalibrierte Wahrscheinlichkeiten.",
        "- Keine Gebühren-/Slippage- oder Ausführungssimulation: verglichen werden Folgeprognosen, keine Handelsentscheidungen oder Strategierenditen.",
        "- Bestehende P0-Probleme (RSI, künstliche Fundamentaldaten, übersteuerbare Regeln) wurden nicht verändert. Der PoC importiert keine Anwendungsmodule und benötigt keine KI-, TradingView- oder Brokerverbindung.",
        "",
        "Datenherkunft, Lizenzerklärung und SHA-256: data/manifest.json und DATA_NOTICE.md. Regeln und Reproduktionsbefehle: README.md.",
        "",
        f"Protokoll-SHA-256 (kanonisches JSON): {payload['protocol_sha256']}",
        f"Datensnapshot-Manifest-SHA-256 (kanonisches JSON): {payload['manifest_sha256']}",
        "",
    ]
    return "\n".join(lines)


def run(output: Path) -> dict:
    cfg = json.loads((HERE / "protocol.json").read_text(encoding="utf-8"))
    series, manifest = load_data(HERE / "data")
    records, structures = evaluate(series, cfg)
    summary = summarize(records, cfg)
    payload = {
        "protocol": cfg,
        "protocol_sha256": digest(cfg),
        "manifest_sha256": digest(manifest),
        "summary": summary,
        "records": records,
        "structures": structures,
        "versions": {
            name: importlib.metadata.version(name) for name in ("numpy", "stumpy", "scipy", "numba")
        },
    }
    output.mkdir(parents=True, exist_ok=True)
    for name, value in (
        ("summary", {k: v for k, v in payload.items() if k not in ("records", "structures")}),
        ("predictions", records),
        ("structures", structures),
    ):
        (output / f"{name}.json").write_text(
            json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    with (output / "predictions.csv").open("w", newline="", encoding="utf-8") as f:
        fields = [
            "symbol",
            "phase",
            "date",
            "query_start",
            "outcome_end",
            "mass",
            "trend",
            "momentum",
            "always_positive",
            "mass_expected_log_return",
            "actual_log_return",
            "close_path_mae",
            "close_path_mfe",
        ]
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)
    (output / "REPORT.md").write_text(report_markdown(payload), encoding="utf-8", newline="\n")
    return summary


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=HERE / "results")
    args = parser.parse_args()
    print(json.dumps(run(args.output), indent=2))
