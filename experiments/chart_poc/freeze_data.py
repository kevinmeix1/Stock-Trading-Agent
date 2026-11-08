"""Explicit acquisition only. The analysis runner is entirely offline."""
from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import urllib.request
from pathlib import Path

COMMIT = "c0ccb5facf6db1c2ee4dffdde80ad9c06bc9b587"
URL = f"https://raw.githubusercontent.com/bokeh/bokeh_sampledata/{COMMIT}/src/bokeh_sampledata/_data/stocks.csv.gz"
EXPECTED = "5abadf99b2d394f920120a27de6f0df129859d71d4cfb0bf661bcc99446ab1fd"
SYMBOLS = ("AAPL", "IBM", "MSFT")
FIELDS = ("date", "open", "high", "low", "close", "volume", "adj_close")

def freeze(destination: Path) -> dict:
    raw = urllib.request.urlopen(URL, timeout=60).read()
    if hashlib.sha256(raw).hexdigest() != EXPECTED:
        raise ValueError("Pinned source checksum mismatch")
    rows = list(csv.DictReader(io.StringIO(gzip.decompress(raw).decode("utf-8"))))
    rows = [{k.lower().replace(" ", "_"): v for k, v in r.items()} for r in rows]
    manifest = {
        "frozen_on": "2026-11-08", "source_url": URL, "source_commit": COMMIT,
        "source_sha256": EXPECTED, "origin": "Quandl WIKI Prices via Bokeh sampledata",
        "source_license": "Public domain (upstream stocks dataset notice)",
        "source_notice": f"https://github.com/bokeh/bokeh_sampledata/blob/{COMMIT}/licenses/datasets.json",
        "currency": "USD", "interval": "1D", "venue": "US primary-market historical daily bars",
        "time": "date-only US session label, no invented intraday timestamp",
        "raw_fields": list(FIELDS), "symbols": [],
        "analysis_adjustment": "OHLC multiplied per row by adj_close/close; volume remains raw, unused in prediction",
        "revision_limit": "retrospective adjusted snapshot, includes subsequent corporate actions; not a point-in-time vendor archive",
    }
    destination.mkdir(parents=True, exist_ok=True)
    for symbol in SYMBOLS:
        selected = [r for r in rows if r["ticker"] == symbol]
        if not selected:
            raise ValueError("Missing symbol: " + symbol)
        stream = io.StringIO(newline="")
        writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows({k: r[k] for k in FIELDS} for r in selected)
        content = stream.getvalue().encode("utf-8")
        path = destination / f"{symbol}.csv"
        if path.exists() and path.read_bytes() != content:
            raise ValueError("Refusing to overwrite a different frozen snapshot: " + symbol)
        path.write_bytes(content)
        manifest["symbols"].append({
            "symbol": symbol, "file": path.name, "rows": len(selected),
            "start": selected[0]["date"], "end": selected[-1]["date"],
            "sha256": hashlib.sha256(content).hexdigest(),
        })
    text = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    path = destination / "manifest.json"
    if path.exists() and path.read_text(encoding="utf-8") != text:
        raise ValueError("Refusing to overwrite a different manifest")
    path.write_text(text, encoding="utf-8")
    return manifest

if __name__ == "__main__":
    result = freeze(Path(__file__).resolve().parent / "data")
    print(json.dumps(result["symbols"], indent=2))
