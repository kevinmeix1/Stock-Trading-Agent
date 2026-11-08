# P0 safety work package

Status: implemented and independently reviewed; separate review PR, no deployment.
Base: `8e9246bdfa87fac2c0ed6f6f488419e699cd043f`.

## Scope and acceptance

Separate review PR only. No deployment, merge, broker access or changes to PR #2
and PR #3. Fix the reproducible RSI boundary case, reject invalid indicator input,
remove fabricated fundamentals, and make risk approval and the portfolio decision
deterministic even with adversarial model replies. Every correction needs regression
evidence. Existing interfaces stay intact except documented validation failures for
invalid/insufficient input and explicit provenance requirements for fundamentals.

## Corrected behavior and interface implications

- Wilder RSI uses the average of the first 14 price changes, then recursive
  smoothing. The first 14 observations are NaN (unavailable), not neutral readings.
  Increasing/decreasing/constant prices yield 100/0/50 after warmup.
- Indicator snapshots require 50 complete valid bars. OHLCV values must be finite,
  prices positive, volume nonnegative, dates unique/chronological and bars feasible.
  Corrupt data raises ValueError; it is not silently forward-filled.
- RiskManager.reason and PortfolioManager.reason are deterministic in online and
  offline mode. They never request model replacements for approval, direction,
  size, stops or targets. A risk rejection carries zero permitted position size.
  Invalid indicator/conviction values cause a zero-size veto.
- No fabricated fundamental fields are generated or stored. Missing, incomplete,
  invalid or future-dated inputs produce signal=0 and confidence=0. Such reports
  are excluded from both the debate evidence and disagreement calculation.
- Caller-provided `ctx.scratchpad['fundamentals']` must contain `symbol`, nonempty
  `source`, ISO date `as_of` no later than the history cutoff, and finite `pe`,
  `rev_growth`, `margin`, `debt_to_equity`. P/E must be positive; growth/margin are
  fractions. This narrow existing earnings-valuation model cannot assess a loss
  maker with nonpositive P/E. It reports unavailable instead of treating it as cheap.
  Provenance is caller supplied, not independently verified by a data provider.
- Risk/portfolio JSON schemas and routes remain unchanged. No LLM-generated
  commentary is added to those deterministic reports in this work package.

## Evidence

The unchanged upstream baseline passed 46 tests. Before the fix, the new targeted
regressions reproduced 25 failures (and one already-correct invalid-window case).
Validation covers exact hand-calculated Wilder values, warmup, future-prefix
invariance, corrupt data, adversarial model replies, mandate direction/limits,
unavailable fundamentals and provenance/cutoff checks. No network/model is used.

Final verification: 83 tests pass (46 unchanged baseline tests and 37 P0 regression
cases), Ruff passes, and git diff --check passes. Independent review found two
additional numeric edge cases: rounding an approved weight upward and overflow
before the extreme-volatility veto. Both were reproduced in failing regressions,
fixed, and independently rechecked (37/37 P0 cases, final verdict PASS).

The existing optional FastAPI TestClient dependency emits a deprecation warning;
it does not affect the test results and no dependencies were changed.

## Follow-up work package

Structure Engine and a separate read-only dashboard explain confirmed HH/HL/LH/LL,
BOS/CHoCH, multi-window trend, RSI/MACD/divergence, confirmed price zones and ATR
distances, objectively confirmed patterns and confluence/conflict. Technical state
is not a price forecast: a weak trend near support is not automatically bullish.
Production integration remains unapproved.

MASS stays isolated in PR #3. Any later forecast experiment must commit its universe,
variants, baselines, metrics and acceptance criteria before new holdout access.
Historical forecast research does not gate the descriptive engine.
