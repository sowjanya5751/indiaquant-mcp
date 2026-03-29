# Decision layer — first draft (signal fusion)

This document describes the **rule-based decision module** added on top of the existing IndiaQuant MCP tools. It matches the scoped collaboration plan: normalized inputs, weighted fusion, cross-tool agreement/conflict handling, and lightweight validation (execution-aware logic and ML weighting are intentionally deferred).

## Architecture (v1)

```
┌─────────────────┐   ┌──────────────────┐   ┌─────────────────┐
│ SignalEngine    │   │ SentimentAnalyzer │   │ OptionsAnalyzer │
│ (technical)     │   │ (news keywords)   │   │ (OI / max pain) │
└────────┬────────┘   └────────┬──────────┘   └────────┬────────┘
         │                     │                        │
         ▼                     ▼                        ▼
    Normalizers (`app/decision/normalizers.py`) → `NormalizedSignal`
         │
         ▼
    `DecisionEngine.fuse` — weighted edge score, agreement / conflict, validation
         │
         ▼
    `MarketDecisionResponse` (direction, edge_score, unified_confidence, execution_hint)
```

## Canonical input: `NormalizedSignal`

| Field | Type | Notes |
|-------|------|--------|
| `source` | `technical` \| `sentiment` \| `options` | One row per module |
| `direction` | `buy` \| `sell` \| `neutral` | Comparable across modules |
| `confidence` | float in `[0, 1]` | Module-specific certainty |
| `metadata` | object | Audit trail (indicators, PCR, errors, etc.) |

Upstream failures (missing data, API not configured) still produce a **low-confidence neutral** signal so the fusion graph stays complete and observable.

## Normalization rules (v1 heuristics)

- **Technical**: Maps existing `BUY` / `SELL` / `HOLD` and scales `confidence` from `0–100` → `0–1`.
- **Sentiment**: Maps `POSITIVE` / `NEGATIVE` / `NEUTRAL`; confidence grows with \|keyword score\|. If `NEWSAPI_KEY` is unset, the module returns a documented error payload → neutral stub.
- **Options**: Uses put/call **open-interest ratio** on the first expiry slice; optional **spot vs max pain** tension adjusts direction/confidence when both numbers exist.

These heuristics are **deterministic** and **configurable** via future parameter objects; they are not claimed as optimal trading rules.

## Fusion

- Per-module weight defaults: technical **0.45**, sentiment **0.30**, options **0.25** (`DecisionWeights`).
- **Edge score** in `[-1, 1]`: weighted sum of `sign(direction) × confidence`, normalized by active weights.
- **Cross-tool conflict**: simultaneous `buy` and `sell` among modules applies a confidence haircut and feeds validation.
- **Alignment boost**: if at least two modules agree on buy (or sell) with no opposing vote, a small confidence bonus is applied (capped).

## Validation (v1)

| Check | Behavior |
|-------|-----------|
| Minimum unified confidence | Reject → `final_direction = neutral`, `execution_hint = no_trade` |
| Conflict + weak edge | Reject when modules disagree and \|edge\| is below `min_edge_magnitude` |
| High realized volatility | Warning + optional confidence penalty (annualized vol from recent closes) |
| Low intraday volume | Warning vs configurable threshold |

Rejection reasons are enumerated in `validation.reasons` for agent-friendly handling.

## HTTP surface (FastAPI)

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/fuse_market_decision` | Body: `FuseDecisionRequest` — runs full pipeline for a symbol |
| `POST` | `/fuse_decision_manual` | Body: `ManualFuseRequest` — fuse pre-normalized signals (tests / custom ingest) |
| `POST` | `/analyze_sentiment` | Exposes sentiment tool (was listed in README; now registered) |
| `GET` | `/schemas/decision_layer` | Bundled **JSON Schema** (Pydantic v2) for all decision I/O models |

OpenAPI UI is at `/docs`; CI runs `pytest` on push (see `.github/workflows/ci.yml`).

**Native MCP:** the same fusion logic is available over **MCP stdio** for AI hosts — run `PYTHONPATH=. python -m app.mcp.stdio_server` (see `README.md` for Claude Desktop config).

## Example: fuse market decision

Request (minimal — NSE symbol without suffix):

```bash
curl -s -X POST "http://127.0.0.1:8000/fuse_market_decision" \
  -H "Content-Type: application/json" \
  -d '{"symbol": "RELIANCE", "include_raw_modules": true}'
```

Request (custom weights + stricter validation):

```json
{
  "symbol": "TCS",
  "weights": { "technical": 0.5, "sentiment": 0.2, "options": 0.3 },
  "validation": { "min_unified_confidence": 0.4, "min_edge_magnitude": 0.15 }
}
```

Response shape (abbreviated): `final_direction`, `edge_score`, `unified_confidence`, `execution_hint`, `agreement`, `validation`, `normalized_signals`, `fusion_notes`.

## Code map

| Path | Role |
|------|------|
| `app/decision/schemas.py` | Pydantic I/O contracts |
| `app/decision/normalizers.py` | Raw tool JSON → `NormalizedSignal` |
| `app/decision/engine.py` | Fusion + validation |
| `app/decision/service.py` | Orchestration + vol/volume context |
| `tests/test_decision_engine.py` | Unit tests (no live network) |

## Environment

- `NEWSAPI_KEY`: required for live NewsAPI sentiment; fusion remains functional without it (neutral sentiment stub).

## Next steps (out of scope for this draft)

- Execution-aware gates (spread, slippage, session windows).
- Virtual-trade feedback loop driving **learned** weights instead of static `DecisionWeights`.

---

*Draft for async review with IndiaQuant MCP — rule-based, interpretable v1.*
