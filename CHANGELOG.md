# Changelog

## [0.2.0] — Decision layer v1 (first draft)

### Added

- **`app/decision/`** — Normalized signal schema (`NormalizedSignal`), configurable `DecisionWeights`, `ValidationConfig`, and `MarketDecisionResponse`.
- **Normalizers** — Map technical (`SignalEngine`), sentiment (`SentimentAnalyzer`), and options (`OptionsAnalyzer`) outputs into a single contract.
- **`DecisionEngine`** — Rule-based weighted fusion, edge score in `[-1, 1]`, cross-module agreement/conflict handling, lightweight validation (confidence, conflict + weak edge, volatility haircut, volume warnings).
- **`DecisionLayerService`** — Orchestrates existing modules plus realized vol / intraday volume context.
- **HTTP** — `POST /fuse_market_decision`, `POST /fuse_decision_manual`, `POST /analyze_sentiment` (registered; was documented but missing).
- **Native MCP (stdio)** — `app/mcp/stdio_server.py` via `python -m app.mcp.stdio_server` using the official `mcp` SDK (`FastMCP`), exposing `fuse_market_decision` and core tools for Claude Desktop / Cursor.
- **`GET /schemas/decision_layer`** — JSON Schema bundle for all decision-layer Pydantic models.
- **Docs** — `docs/decision_layer_first_draft.md` (architecture, schema, examples).
- **Tests** — `tests/test_decision_engine.py` (no network).
- **Tooling** — `pytest.ini`, `.github/workflows/ci.yml`.

### Changed

- **Sentiment** — `NEWSAPI_KEY` read from environment (no hardcoded API key). If unset, sentiment degrades to a neutral stub; fusion still runs.

### Deferred (aligned with collaboration scope)

- Execution-aware gates (spreads, session timing, full tradeability model).
- Feedback loop / ML-learned weights from virtual-trade outcomes.

---

## [0.1.0] — Baseline

- FastAPI MCP-style HTTP tools: market data, signals, options, Greeks, portfolio, scanner, heatmap, sentiment (module present), unusual activity.
