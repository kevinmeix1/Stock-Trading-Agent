"""Regression oracles for independently reproduced P0 failures; no model/network."""

import numpy as np
import pandas as pd
import pytest

from stock_trading_agent.agents.analysts import FundamentalAnalyst
from stock_trading_agent.agents.base import AgentContext
from stock_trading_agent.agents.researchers import ResearchDebate
from stock_trading_agent.agents.risk import RiskManager
from stock_trading_agent.agents.schemas import Action, AnalystReport, DebateResult, RiskAssessment
from stock_trading_agent.agents.trader import PortfolioManager
from stock_trading_agent.data.indicators import compute_indicators, rsi
from stock_trading_agent.data.types import PriceHistory
from stock_trading_agent.llm.offline import OfflineChatModel


class AdversarialModel(OfflineChatModel):
    def structured(self, **kwargs):
        return {**kwargs["fallback"], "approved": True, "position_size_pct": 1.,
                "action": "BUY", "target_weight": 1., "stop_loss_pct": 0.,
                "take_profit_pct": 2., "signal": 1., "confidence": 1.,
                "rationale": "Ignore the rules and buy."}


def context(history, settings, conviction=.8):
    ctx = AgentContext(symbol=history.symbol, history=history,
                       indicators=compute_indicators(history), settings=settings)
    ctx.remember("debate", DebateResult(bull_thesis="b", bear_thesis="s", rounds=1,
                                       judge_summary="test", conviction=conviction))
    return ctx


@pytest.mark.parametrize("prices,expected", [
    (np.arange(1., 61.), 100.), (np.arange(60., 0., -1.), 0.), (np.ones(60), 50.),
])
def test_rsi_extremes_and_explicit_warmup(prices, expected):
    values = rsi(pd.Series(prices))
    assert values.iloc[:14].isna().all()
    assert (values.iloc[14:] == expected).all()


def test_rsi_wilder_seed_and_recursive_smoothing():
    # Three gains/losses: avg gain=2/3, avg loss=1/3 -> RSI=66 2/3.
    prices = pd.Series([10., 11., 10., 11., 13., 12.])
    result = rsi(prices, window=3)
    assert result.iloc[3] == pytest.approx(100 * 2 / 3)
    assert result.iloc[4] == pytest.approx(100 * 5 / 6)
    assert result.iloc[5] == pytest.approx(100 * 20 / 33)
    pd.testing.assert_series_equal(result.iloc[:4], rsi(prices.iloc[:4], window=3))


@pytest.mark.parametrize("window", [0, -1, 1.5, True])
def test_rsi_rejects_invalid_window(window):
    with pytest.raises(ValueError):
        rsi(pd.Series([1., 2., 3.]), window)


@pytest.mark.parametrize("bad", [np.nan, np.inf, -1., 0.])
def test_price_history_rejects_invalid_values(history, bad):
    frame = history.frame.copy()
    frame.iloc[-1, frame.columns.get_loc("close")] = bad
    with pytest.raises(ValueError):
        PriceHistory(history.symbol, frame)


def test_price_history_rejects_duplicates_impossible_bars_and_negative_volume(history):
    for kind in ("duplicate", "bar", "volume", "empty", "nat"):
        frame = history.frame.copy()
        if kind == "duplicate":
            frame = pd.concat([frame, frame.iloc[-1:]])
        elif kind == "bar":
            frame.iloc[-1, frame.columns.get_loc("high")] = frame.close.iloc[-1] / 2
        elif kind == "volume":
            frame.iloc[-1, frame.columns.get_loc("volume")] = -1
        elif kind == "empty":
            frame = frame.iloc[:0]
        else:
            frame.index = [*frame.index[:-1], pd.NaT]
        with pytest.raises(ValueError):
            PriceHistory(history.symbol, frame)


def test_snapshot_requires_50_complete_bars_and_revalidates_mutated_history(history):
    with pytest.raises(ValueError, match="50"):
        compute_indicators(PriceHistory(history.symbol, history.frame.iloc[:49].copy()))
    damaged = PriceHistory(history.symbol, history.frame.copy())
    damaged.frame.iloc[-1, damaged.frame.columns.get_loc("close")] = np.inf
    with pytest.raises(ValueError):
        compute_indicators(damaged)


@pytest.mark.parametrize("conviction,vol", [(0., .2), (.8, 1.2), (.8, np.nan), (.8, 1e200)])
def test_model_cannot_reverse_risk_veto(history, settings, conviction, vol):
    ctx = context(history, settings, conviction)
    ctx.indicators.annualised_vol = vol
    risk = RiskManager(AdversarialModel(), settings).assess(ctx)
    assert risk.approved is False
    assert risk.position_size_pct == 0.


def test_model_cannot_change_valid_deterministic_limits(history, settings):
    ctx = context(history, settings)
    expected = RiskManager(OfflineChatModel(), settings, max_position=.25).assess(ctx)
    actual = RiskManager(AdversarialModel(), settings, max_position=.25).assess(ctx)
    assert actual == expected
    assert actual.stop_loss_pct > 0
    assert actual.position_size_pct <= .25


@pytest.mark.parametrize("risk_exists,approved", [(False, False), (True, False), (True, True)])
def test_model_cannot_bypass_final_mandate(history, settings, risk_exists, approved):
    ctx = context(history, settings)
    if risk_exists:
        ctx.remember("risk", RiskAssessment(approved=approved, position_size_pct=.12,
                     stop_loss_pct=.07, take_profit_pct=.14, rationale="fixed"))
    expected = PortfolioManager(OfflineChatModel(), settings).decide(ctx)
    actual = PortfolioManager(AdversarialModel(), settings).decide(ctx)
    assert actual == expected
    if not approved:
        assert actual.action == Action.HOLD
        assert actual.target_weight == 0.
    else:
        assert actual.target_weight == .12
        assert actual.stop_loss_pct == .07
        assert actual.take_profit_pct == .14


@pytest.mark.parametrize("fundamentals", [None, {}, {"pe": 12.},
    {"pe": 12., "rev_growth": .2, "margin": .1, "debt_to_equity": .5},
])
def test_no_fabricated_or_unsourced_fundamental_opinion(history, settings, fundamentals):
    ctx = context(history, settings)
    if fundamentals is not None:
        ctx.remember("fundamentals", fundamentals)
    report = FundamentalAnalyst(AdversarialModel(), settings).analyze(ctx)
    assert report.signal == report.confidence == 0.
    assert "unavailable" in report.rationale.lower()
    assert ctx.scratchpad.get("fundamentals") == fundamentals


def test_provenanced_fundamentals_are_accepted_only_as_of_history(history, settings):
    ctx = context(history, settings)
    facts = {"symbol": history.symbol, "source": "caller-provided annual report",
             "as_of": history.end.date().isoformat(), "pe": 12., "rev_growth": .2,
             "margin": .1, "debt_to_equity": .5}
    ctx.remember("fundamentals", facts)
    assert FundamentalAnalyst(OfflineChatModel(), settings).analyze(ctx).confidence > 0
    for changes in ({"symbol": "OTHER"}, {"pe": np.nan}, {"pe": True},
                    {"as_of": "2099-01-01"}, {"source": ""}):
        ctx.remember("fundamentals", {**facts, **changes})
        assert FundamentalAnalyst(AdversarialModel(), settings).analyze(ctx).confidence == 0


def test_missing_fundamentals_do_not_act_as_a_neutral_vote():
    real = AnalystReport(agent="technical", signal=.8, confidence=.7, rationale="facts")
    missing = AnalystReport(agent="fundamental", signal=0., confidence=0., rationale="missing")
    assert ResearchDebate._weighted_conviction([real, missing]) == ResearchDebate._weighted_conviction([real])


@pytest.mark.parametrize("conviction,expected_action", [(-.8, Action.SELL), (0., Action.HOLD), (.8, Action.BUY)])
def test_model_cannot_change_direction_or_neutral_band(history, settings, conviction, expected_action):
    ctx = context(history, settings, conviction)
    ctx.remember("risk", RiskAssessment(approved=True, position_size_pct=.12,
                 stop_loss_pct=.07, take_profit_pct=.14, rationale="fixed"))
    decision = PortfolioManager(AdversarialModel(), settings).decide(ctx)
    assert decision.action == expected_action
    assert decision.target_weight == (0. if expected_action == Action.HOLD else .12)


@pytest.mark.parametrize("key", ["target_volatility", "max_position", "max_asset_vol", "min_conviction", "kelly_fraction"])
def test_nonfinite_policy_rejected(settings, key):
    with pytest.raises(ValueError):
        RiskManager(AdversarialModel(), settings, **{key: np.nan})


def test_final_weight_cannot_round_up_above_exact_risk_limit(history, settings):
    ctx = context(history, settings)
    risk = RiskManager(AdversarialModel(), settings, max_position=.12345).assess(ctx)
    decision = PortfolioManager(AdversarialModel(), settings).decide(ctx)
    assert decision.target_weight <= risk.position_size_pct <= .12345
