"""Explicit local CSV -> JSON + standalone HTML, with content fingerprints."""

from __future__ import annotations

import argparse
import hashlib
import json
from io import BytesIO
from pathlib import Path

import numpy as np
import pandas as pd

from .engine import analyze


def load_csv(
    path: Path, *, expected_sha256: str | None = None, adjusted: bool = False
) -> tuple[pd.DataFrame, str]:
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if expected_sha256 is not None and digest != expected_sha256.lower():
        raise ValueError("CSV SHA-256 does not match the supplied checksum.")
    frame = pd.read_csv(BytesIO(raw))
    frame.index = pd.to_datetime(frame.pop("date"), format="%Y-%m-%d", errors="raise")
    if adjusted:
        if "adj_close" not in frame:
            raise ValueError("--adjusted requires an explicit adj_close column.")
        factor = frame.adj_close / frame.close
        if not np.isfinite(factor).all() or (factor <= 0).any():
            raise ValueError("Invalid adjustment factors.")
        frame[["open", "high", "low", "close"]] = frame[["open", "high", "low", "close"]].mul(
            factor, axis=0
        )
    return frame, digest


def html_report(report: dict) -> str:
    assets = Path(__file__).parent
    template = (assets / "view.html").read_text(encoding="utf-8")
    payload = (
        json.dumps(report, ensure_ascii=False, allow_nan=False)
        .replace("<", "\\u003c")
        .replace("&", "\\u0026")
    )
    return (
        template.replace("/*STYLE*/", (assets / "view.css").read_text(encoding="utf-8"))
        .replace("/*SCRIPT*/", (assets / "view.js").read_text(encoding="utf-8"))
        .replace("/*DATA*/", payload)
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", required=True, type=Path)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--currency", required=True)
    parser.add_argument("--sha256")
    parser.add_argument("--adjusted", action="store_true")
    parser.add_argument(
        "--as-of", help="Inclusive date cutoff YYYY-MM-DD, applied before calculation"
    )
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    frame, digest = load_csv(args.csv, expected_sha256=args.sha256, adjusted=args.adjusted)
    if args.as_of:
        cutoff = pd.to_datetime(args.as_of, format="%Y-%m-%d", errors="raise")
        frame = frame.loc[frame.index <= cutoff].copy()
    adjustment = (
        "OHLC × adj_close/close from retrospective adjusted snapshot; volume unadjusted"
        if args.adjusted
        else "Unadjusted OHLC as supplied"
    )
    report = analyze(
        frame, symbol=args.symbol, source=args.source, currency=args.currency, adjustment=adjustment
    )
    report["dataset"] = {
        "sha256": digest,
        "checksum_verified": args.sha256 is not None,
        "cutoff": args.as_of,
        "source_file": args.csv.name,
    }
    args.output.mkdir(parents=True, exist_ok=True)
    if any((args.output / name).exists() for name in ("report.json", "index.html")):
        raise FileExistsError("Output already contains a report; choose a fresh output directory.")
    (args.output / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    (args.output / "index.html").write_text(html_report(report), encoding="utf-8")
    print(
        json.dumps(
            {
                "symbol": args.symbol,
                "as_of": report["as_of"],
                "technical_state": report["assessment"]["state"],
                "sha256": digest,
                "bars": len(frame),
            }
        )
    )


if __name__ == "__main__":
    main()
