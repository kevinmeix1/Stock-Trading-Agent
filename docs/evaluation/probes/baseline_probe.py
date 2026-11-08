"""Read-only evaluation probes for upstream commit 8e9246b; not production fixes.

Prints observed behavior, including known defects. An assertion failure means
the audited baseline has changed and the findings must be reviewed.
No network calls, credentials, orders or persistent reflection memory.
"""

from __future__ import annotations

import json

import pandas as pd

from stock_trading_agent.agents.base import AgentContext
from stock_trading_agent.agents.risk import RiskManager
from stock_trading_agent.agents.schemas import RiskAssessment
from stock_trading_agent.agents.trader import PortfolioManager
from stock_trading_agent.config import LLMProvider, Settings
from stock_trading_agent.data.indicators import compute_indicators, rsi
from stock_trading_agent.data.market import SyntheticMarketDataProvider
from stock_trading_agent.data.types import PriceHistory
from stock_trading_agent.llm.base import ChatModel


class ControlledModel(ChatModel):
    """Returns a deliberate contradiction to test enforcement, not model skill."""

    def chat(self, messages, *, temperature=None, max_tokens=None):
        return json.dumps(
            {
                "approved": True,
                "position_size_pct": 0.3,
                "stop_loss_pct": 0.05,
                "take_profit_pct": 0.1,
                "action": "BUY",
                "target_weight": 1.0,
                "confidence": 1.0,
                "rationale": "Synthetic enforcement probe",
                "flags": [],
            }
        )


def main():
    settings = Settings(
        _env_file=None,
        llm_provider=LLMProvider.OFFLINE,
        openai_api_key=None,
        anthropic_api_key=None,
        verbose=False,
    )
    observed_rsi = float(rsi(pd.Series(range(100, 140), dtype=float)).iloc[-1])
    assert observed_rsi == 50.0

    history = SyntheticMarketDataProvider(base_seed=42).history("SYNTH", lookback_days=120)
    context = AgentContext(
        symbol="SYNTH",
        history=history,
        indicators=compute_indicators(history),
        settings=settings,
    )
    manager = RiskManager(ControlledModel(), settings)
    heuristic_rejected = manager.heuristic(context)["approved"] is False
    model_approved = manager.assess(context).approved
    assert heuristic_rejected and model_approved

    context.remember(
        "risk",
        RiskAssessment(
            approved=False,
            position_size_pct=0,
            stop_loss_pct=0,
            take_profit_pct=0,
            rationale="Synthetic rejection",
        ),
    )
    decision = PortfolioManager(ControlledModel(), settings).decide(context)
    assert decision.action.value == "BUY" and decision.target_weight == 1.0

    invalid = pd.DataFrame(
        {
            "open": [10, 10],
            "high": [9, 9],
            "low": [11, 11],
            "close": [10, float("nan")],
            "volume": [-1, -1],
        },
        index=pd.to_datetime(["2020-01-01", "2020-01-01"]),
    )
    accepted = PriceHistory(symbol="SYNTH", frame=invalid)
    assert len(accepted) == 2 and accepted.frame.index.has_duplicates

    result = {
        "baseline_commit": "8e9246bdfa87fac2c0ed6f6f488419e699cd043f",
        "fixture": "SIMULATED_ONLY",
        "rsi_strictly_rising_40_bars": observed_rsi,
        "rsi_expected_after_warmup": 100.0,
        "risk_heuristic_rejected": heuristic_rejected,
        "risk_model_can_override_rejection": model_approved,
        "portfolio_manager_with_rejected_risk": {
            "action": decision.action.value,
            "weight": decision.target_weight,
        },
        "duplicate_nan_invalid_ohlcv_accepted": True,
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
