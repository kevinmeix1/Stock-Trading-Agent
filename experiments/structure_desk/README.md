# Read-only Structure Desk

Scope: descriptive technical analysis and a standalone local HTML dashboard.
Work package 2 follows P0 PR #4; it does not deploy or merge that change. PR #2
and PR #3 stay untouched. No imports from production analysis/decision modules,
MASS, TradingView, LLMs or brokers. No extra dependencies. All commands are explicit
local file operations; there is no listener, background refresh or live connection.

Acceptance: causally confirmed HH/HL/LH/LL, close-based BOS/CHoCH, multiple trend
windows and efficiency, RSI/MACD and confirmed-pivot divergences, confirmed support/
resistance zones with ATR distances, confirmed double-bottom/top formations,
confluence/conflicts, and a reasoned BULLISH/NEUTRAL/BEARISH technical state.
There are no forecasts, targets, trade decisions or future outcomes in the report.

## Reproduce

Use Python 3.10+ with the application's existing pandas/numpy and pytest tooling.
No optional quant, model or data-provider extras are needed.

```text
python -m pytest tests experiments/structure_desk/test_engine.py
python -m ruff check experiments/structure_desk
node --check experiments/structure_desk/view.js
python -m experiments.structure_desk --csv path/to/closed-daily-bars.csv --symbol EXAMPLE --source "source name and snapshot date" --currency USD --output path/to/fresh-report
```

Open `path/to/fresh-report/index.html` directly in a browser. It is a self-contained
file, including its data, script and style. `report.json` is the machine-readable
equivalent. Input CSV columns: `date,open,high,low,close,volume`; dates ISO YYYY-MM-DD
in ascending unique order. At least 50 finite, feasible, complete bars are required;
205 are needed for all trend windows including the five-session SMA200 slope.

`--as-of YYYY-MM-DD` truncates before any calculation. `--sha256 HEX` verifies an
expected source digest; without it the digest is only a content fingerprint, which
the dashboard explicitly distinguishes. Existing report files are not overwritten.
`--adjusted` requires `adj_close`; OHLC are multiplied by the row's `adj_close/close`
factor, volume stays raw and is not used in the assessment. This is a retrospectively
adjusted snapshot, not proof of point-in-time availability of corporate adjustments.
Completed daily sessions are an input contract, not verified against an exchange
calendar. Never label an intraday bar a completed session when preparing the CSV.

### Known historical demo sources

`demo-sources.json` references the exact files and SHA-256 values from PoC commit
`89933382e8aaf0730bf98e9b342e190a5a396651`. AAPL/IBM/MSFT have 3270 rows each,
2000-03-01 through 2013-03-01. These are already examined historical observations,
not current quotes or a new untouched holdout. The Structure Desk does not import
or run the PoC or MASS. CSVs are not duplicated in this PR.

To reproduce the smoke reports, obtain those exact CSVs from the pinned GitHub
commit, check their manifest hashes and use the command above with `--sha256`,
`--adjusted`, symbol, USD and the source label from `demo-sources.json`.
All subsequent calculations and HTML viewing run offline.

## Fixed descriptive rules

- **Swings:** strict three-left/three-right high or low. First comparable pivots
  are H/L, then HH/LH and HL/LL; equal levels EH/EL. Flat extremes and ambiguous
  simultaneous high/low pivots are excluded. A pivot is available only three bars
  later. The chart places its marker at origin; the event list exposes both dates.
- **BOS/CHoCH:** close crosses the latest already confirmed unbroken swing level;
  wicks do not count. The first break establishes direction and is marked initial.
  Same-direction breaks are BOS; an opposite-direction break is CHoCH. One break
  per swing. Structure direction is the latest confirmed break, not a forecast.
- **Trend:** SMA20/50/200, above/below SMA and its five-bar slope must agree for a
  directional state; otherwise neutral. Strength is directional efficiency over
  20/50/200 sessions: absolute net move / sum of absolute daily moves, in [0,1].
  It measures directional persistence, not future return or trend probability.
- **Momentum:** Wilder RSI14 uses 14 changes as SMA seed, then recursive smoothing;
  rising/falling/flat is 100/0/50 after warmup. EMA12/26 and signal9 produce MACD;
  EMA seeds at the first supplied close. Histogram sign is the momentum vote.
  RSI >70 / <30 is overbought/oversold context, not a directional vote.
- **ATR:** 14 true ranges, SMA seed and Wilder recursion. All indicator warmups
  use supplied history before the displayed final 252 sessions.
- **Zones:** two confirmed same-kind pivots at least five sessions apart; their
  prices differ by at most 0.5 ATR measured at the second pivot confirmation.
  Bounds are min/max pivot price padded by 0.25 of that ATR. Bounds and establishment
  date freeze at that moment; later touches within the bounds do not widen them.
  A candidate's initial guard uses its first confirmation ATR. Any close below
  support/above resistance invalidates its earlier touches permanently. A new zone
  needs two fresh post-break confirmations; no automatic support/resistance flip.
  Zones with a touch in the final 252 sessions remain in the report. Status is
  evaluated at report cutoff, and current distance uses current ATR. Zero ATR
  produces no normalized zone distance or zone. Shading starts at establishment.
- **Divergences:** consecutive same-kind confirmed pivots no more than60 bars
  apart; lower price low with RSI at least3 points higher, or higher high with RSI
  at least3 points lower. Event availability is the second pivot confirmation.
  These are historical regular RSI divergences, not a reversal prediction.
- **Patterns:** consecutive same-kind pivots 5–60 bars apart and within0.75 ATR
  (ATR at second confirmation), with a confirmed intervening neckline and at least
  2 ATR height. Only a subsequent close across the neckline within40 bars after
  second confirmation creates a Double Bottom/Top. A close beyond the extremes
  by0.5 ATR invalidates it. No formation targets or probabilities are calculated.
- **Confluence:** majority of available trend windows is one vote; latest structure
  break is one; MACD histogram is one. At least two matching directional votes give
  BULLISH/BEARISH, else NEUTRAL. Each vote is visible. Support proximity, RSI extremes,
  divergences and old patterns do not independently turn a weak state bullish.
  Bullish and bearish disagreements remain visible, including bearish near support.

The votes are an explicit deterministic descriptive policy, not a trained model
or calibrated probability. Pattern and divergence lists show historical events
with dates rather than implying every old formation remains active today.

## Validation and delivery

74 tests pass: 46 unchanged baseline tests and28 isolated Structure Desk cases.
They cover hand-calculated RSI/ATR, exact swings, confirmation lag, strict ties,
wick versus close breaks, CHoCH direction, missing/invalid data, two-touch zones,
between-touch invalidation, immutable geometry under future volatility, no-future
event/indicator mutation, double-bottom/top confirmation, divergence thresholds,
bearish near support/oversold, checksum/adjustment, HTML injection safety, date
cutoff and byte-identical regeneration. Ruff and JavaScript syntax checks pass.

Independent review PASS after correcting the two zone findings and rerunning all
74 tests. Additional reviewer probes cover post-break reconfirmation and mirrored
resistance invalidation. Three real frozen CSV smoke reports verify their hashes.
Browser QA: price/RSI plots, pivot dates, zone establishment and assessment/conflicts;
360px and1440px show no horizontal overflow or invalid SVG coordinates; no script
errors observed. Local preview uses a temporary loopback server, stopped after QA.

Delivery is this source directory plus reproducible HTML/JSON exports, in a separate
PR left open. No production modules, settings, API routes, interfaces or dependencies
change. The P0 PR remains separate; no decision pipeline is invoked here. Predictive
research and any live-data/production integration remain outside this package.
