# Quellen und Prüfstand

Stand: 8. November 2026. Repositories wurden auf dem unten verlinkten Commit geprüft. Der JSON-Lock enthält zusätzlich die inspizierten Pfade. Code-/Dokumentationsprüfung und lokal ausgeführte Tests sind im [Validierungsprotokoll](VALIDATION.md) getrennt ausgewiesen.

| Projekt | Commitdatum UTC | Geprüfter Stand |
|---|---|---|
| kevinmeix1/Stock-Trading-Agent | 2026-06-29T11:58:45Z | [8e9246bdfa87](https://github.com/kevinmeix1/Stock-Trading-Agent/tree/8e9246bdfa87fac2c0ed6f6f488419e699cd043f) |
| tradesdontlie/tradingview-mcp | 2026-07-28T17:28:37Z | [c05b8f5755ed](https://github.com/tradesdontlie/tradingview-mcp/tree/c05b8f5755ed8e64ea242de88ddbf46aa24d56a4) |
| stophobia/TradingView-MCP2 | 2026-09-10T23:26:47Z | [56334ec1c187](https://github.com/stophobia/TradingView-MCP2/tree/56334ec1c187661c4ee593e263b1450d390a024d) |
| atilaahmettaner/tradingview-mcp | 2026-11-07T14:05:59Z | [e8fdb9b9a23b](https://github.com/atilaahmettaner/tradingview-mcp/tree/e8fdb9b9a23b4389df7cd62e1d90b238ed690101) |
| moeuu/tradingview-mcp | 2026-08-22T07:20:28Z | [a25367d37a93](https://github.com/moeuu/tradingview-mcp/tree/a25367d37a930e680d752fb561e2d7ff0f0df950) |
| TA-Lib/ta-lib-python | 2026-11-05T18:08:12Z | [c42d29c9862e](https://github.com/TA-Lib/ta-lib-python/tree/c42d29c9862e5884f42bf92d2e5a98018a9839f0) |
| xgboosted/pandas-ta-classic | 2026-10-31T09:32:09Z | [ee71ae7b044d](https://github.com/xgboosted/pandas-ta-classic/tree/ee71ae7b044d54ef0e628d82192dfd3c00e4ccc3) |
| white07S/TradingPatternScanner | 2023-08-02T02:48:07Z | [57e5396c4c54](https://github.com/white07S/TradingPatternScanner/tree/57e5396c4c5446c8222ed01ca8ebeefc679d611e) |
| joshyattridge/smart-money-concepts | 2026-04-03T14:16:50Z | [1b62fd6c41e1](https://github.com/joshyattridge/smart-money-concepts/tree/1b62fd6c41e1f508e7ed76831a039fa4c82d42f6) |
| stumpy-dev/stumpy | 2026-11-08T01:45:01Z | [51475d62c532](https://github.com/stumpy-dev/stumpy/tree/51475d62c5323f9923b0d55fdbbd527a77a18c9d) |
| tslearn-team/tslearn | 2026-11-06T10:43:05Z | [a7f1df1a9175](https://github.com/tslearn-team/tslearn/tree/a7f1df1a9175892db7a5bd1021ca53849b4d144a) |
| wannesm/dtaidistance | 2026-10-07T10:39:30Z | [7973dda1845a](https://github.com/wannesm/dtaidistance/tree/7973dda1845a4bc24cd1b2c14939f1d64d461b68) |
| polakowo/vectorbt | 2026-11-07T17:42:26Z | [8a4c61a3562d](https://github.com/polakowo/vectorbt/tree/8a4c61a3562d4200b926a65e95f5c19c655c435e) |
| mementum/backtrader | 2023-04-19T14:13:08Z | [b853d7c90b67](https://github.com/mementum/backtrader/tree/b853d7c90b6721476eb5a5ea3135224e33db1f14) |
| kernc/backtesting.py | 2026-08-05T12:39:16Z | [ca2e2611621e](https://github.com/kernc/backtesting.py/tree/ca2e2611621e472542ba90f7243a1fa06a7d7108) |
| TauricResearch/TradingAgents | 2026-11-04T10:13:55Z | [9fa1196fffbc](https://github.com/TauricResearch/TradingAgents/tree/9fa1196fffbcfd9de5146d2dd2869df84ab99838) |
| AI4Finance-Foundation/FinRobot | 2026-10-24T13:58:26Z | [63e1884a42ea](https://github.com/AI4Finance-Foundation/FinRobot/tree/63e1884a42ea7b729551a5424b4bd6a65af636e0) |

## Entscheidende Quellpfade

### kevinmeix1/Stock-Trading-Agent

- [stock_trading_agent/data/indicators.py](https://github.com/kevinmeix1/Stock-Trading-Agent/blob/8e9246bdfa87fac2c0ed6f6f488419e699cd043f/stock_trading_agent/data/indicators.py)
- [stock_trading_agent/data/types.py](https://github.com/kevinmeix1/Stock-Trading-Agent/blob/8e9246bdfa87fac2c0ed6f6f488419e699cd043f/stock_trading_agent/data/types.py)
- [stock_trading_agent/agents/analysts.py](https://github.com/kevinmeix1/Stock-Trading-Agent/blob/8e9246bdfa87fac2c0ed6f6f488419e699cd043f/stock_trading_agent/agents/analysts.py)
- [stock_trading_agent/agents/risk.py](https://github.com/kevinmeix1/Stock-Trading-Agent/blob/8e9246bdfa87fac2c0ed6f6f488419e699cd043f/stock_trading_agent/agents/risk.py)
- [stock_trading_agent/agents/trader.py](https://github.com/kevinmeix1/Stock-Trading-Agent/blob/8e9246bdfa87fac2c0ed6f6f488419e699cd043f/stock_trading_agent/agents/trader.py)
- [stock_trading_agent/backtest/engine.py](https://github.com/kevinmeix1/Stock-Trading-Agent/blob/8e9246bdfa87fac2c0ed6f6f488419e699cd043f/stock_trading_agent/backtest/engine.py)
- [stock_trading_agent/backtest/metrics.py](https://github.com/kevinmeix1/Stock-Trading-Agent/blob/8e9246bdfa87fac2c0ed6f6f488419e699cd043f/stock_trading_agent/backtest/metrics.py)
- [stock_trading_agent/memory/store.py](https://github.com/kevinmeix1/Stock-Trading-Agent/blob/8e9246bdfa87fac2c0ed6f6f488419e699cd043f/stock_trading_agent/memory/store.py)
- [stock_trading_agent/llm/providers.py](https://github.com/kevinmeix1/Stock-Trading-Agent/blob/8e9246bdfa87fac2c0ed6f6f488419e699cd043f/stock_trading_agent/llm/providers.py)
- [tests/test_backtest.py](https://github.com/kevinmeix1/Stock-Trading-Agent/blob/8e9246bdfa87fac2c0ed6f6f488419e699cd043f/tests/test_backtest.py)

### tradesdontlie/tradingview-mcp

- [src/connection.js](https://github.com/tradesdontlie/tradingview-mcp/blob/c05b8f5755ed8e64ea242de88ddbf46aa24d56a4/src/connection.js)
- [src/core/data.js](https://github.com/tradesdontlie/tradingview-mcp/blob/c05b8f5755ed8e64ea242de88ddbf46aa24d56a4/src/core/data.js)
- [tests/chart_history.test.js](https://github.com/tradesdontlie/tradingview-mcp/blob/c05b8f5755ed8e64ea242de88ddbf46aa24d56a4/tests/chart_history.test.js)
- [LICENSE](https://github.com/tradesdontlie/tradingview-mcp/blob/c05b8f5755ed8e64ea242de88ddbf46aa24d56a4/LICENSE)

### stophobia/TradingView-MCP2

- [src/priceActionContext.ts](https://github.com/stophobia/TradingView-MCP2/blob/56334ec1c187661c4ee593e263b1450d390a024d/src/priceActionContext.ts)
- [src/walkForward.ts](https://github.com/stophobia/TradingView-MCP2/blob/56334ec1c187661c4ee593e263b1450d390a024d/src/walkForward.ts)
- [src/indicatorAudit.ts](https://github.com/stophobia/TradingView-MCP2/blob/56334ec1c187661c4ee593e263b1450d390a024d/src/indicatorAudit.ts)
- [docs/WINDOWS.md](https://github.com/stophobia/TradingView-MCP2/blob/56334ec1c187661c4ee593e263b1450d390a024d/docs/WINDOWS.md)

### atilaahmettaner/tradingview-mcp

- [src/tradingview_mcp/core/services/indicators.py](https://github.com/atilaahmettaner/tradingview-mcp/blob/e8fdb9b9a23b4389df7cd62e1d90b238ed690101/src/tradingview_mcp/core/services/indicators.py)
- [src/tradingview_mcp/core/services/smart_money_service.py](https://github.com/atilaahmettaner/tradingview-mcp/blob/e8fdb9b9a23b4389df7cd62e1d90b238ed690101/src/tradingview_mcp/core/services/smart_money_service.py)
- [src/tradingview_mcp/core/services/backtest_service.py](https://github.com/atilaahmettaner/tradingview-mcp/blob/e8fdb9b9a23b4389df7cd62e1d90b238ed690101/src/tradingview_mcp/core/services/backtest_service.py)

### moeuu/tradingview-mcp

- [src/analysis.ts](https://github.com/moeuu/tradingview-mcp/blob/a25367d37a930e680d752fb561e2d7ff0f0df950/src/analysis.ts)
- [src/market-service.ts](https://github.com/moeuu/tradingview-mcp/blob/a25367d37a930e680d752fb561e2d7ff0f0df950/src/market-service.ts)
- [src/tradingview-browser.ts](https://github.com/moeuu/tradingview-mcp/blob/a25367d37a930e680d752fb561e2d7ff0f0df950/src/tradingview-browser.ts)

### white07S/TradingPatternScanner

- [tradingpatterns/tradingpatterns.py](https://github.com/white07S/TradingPatternScanner/blob/57e5396c4c5446c8222ed01ca8ebeefc679d611e/tradingpatterns/tradingpatterns.py)
- [tradingpatterns/tradingpatterns_tech.py](https://github.com/white07S/TradingPatternScanner/blob/57e5396c4c5446c8222ed01ca8ebeefc679d611e/tradingpatterns/tradingpatterns_tech.py)
- [LICENSE.md](https://github.com/white07S/TradingPatternScanner/blob/57e5396c4c5446c8222ed01ca8ebeefc679d611e/LICENSE.md)

### joshyattridge/smart-money-concepts

- [smartmoneyconcepts/smc.py](https://github.com/joshyattridge/smart-money-concepts/blob/1b62fd6c41e1f508e7ed76831a039fa4c82d42f6/smartmoneyconcepts/smc.py)

### polakowo/vectorbt

- [LICENSE.md](https://github.com/polakowo/vectorbt/blob/8a4c61a3562d4200b926a65e95f5c19c655c435e/LICENSE.md)

### AI4Finance-Foundation/FinRobot

- [setup.py](https://github.com/AI4Finance-Foundation/FinRobot/blob/63e1884a42ea7b729551a5424b4bd6a65af636e0/setup.py)

## Primärdokumentation außerhalb der Code-Repositories

- [Offizieller TradingView-MCP: Berechtigung und Toolkatalog](https://www.tradingview.com/mcp/docs)
- [DeepSeek: API-Vertrag](https://api-docs.deepseek.com/)
- [STUMPY: MASS und Pattern Matching](https://stumpy.readthedocs.io/en/latest/Tutorial_Pattern_Matching.html)
- [tslearn: DTW und Pfadbegrenzungen](https://tslearn.readthedocs.io/en/stable/user_guide/dtw.html)
- [pandas-ta-Maintainer: Projektumzug und Veröffentlichungsmodell](https://github.com/twopirllc/twopirllc)

Die externen Dokumentationsseiten sind nicht commitgepinnt; ihre Aussagen gelten für den Abrufstand. Kostenpflichtige Dienste wurden weder abonniert noch verbunden. Der offizielle TradingView-MCP wurde anhand der Dokumentation geprüft, nicht mit einem bezahlten Account aufgerufen.
