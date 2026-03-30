"""
Official Model Context Protocol (MCP) entrypoint over stdio.

Use with Claude Desktop, Cursor, or other MCP hosts. Keeps the same business logic
as the FastAPI app (`mcp_server.py`) while exposing tools on the wire protocol.

Run from repo root:

    PYTHONPATH=. python -m app.mcp.stdio_server
"""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from app.analytics.sentiment_service import SentimentAnalyzer
from app.decision.schemas import FuseDecisionRequest
from app.decision.service import DecisionLayerService
from app.market_data.market_data_service import MarketDataService
from app.options.options_service import OptionsAnalyzer
from app.signals.signal_service import SignalEngine

mcp = FastMCP(
    "IndiaQuant",
    instructions=(
        "IndiaQuant financial intelligence: live prices, technical signals, "
        "sentiment, options context, and a fused decision layer (v1 rule-based)."
    ),
)

_market = MarketDataService()
_signals = SignalEngine()
_options = OptionsAnalyzer()
_sentiment = SentimentAnalyzer()
_decision = DecisionLayerService(
    signals_engine=_signals,
    options=_options,
    sentiment_analyzer=_sentiment,
)


def _json(data: object) -> str:
    if hasattr(data, "model_dump"):
        payload = data.model_dump(mode="json")
    else:
        payload = data
    return json.dumps(payload, indent=2, default=str)


@mcp.tool()
def fuse_market_decision(symbol: str) -> str:
    """
    Decision layer v1: combine technical signals, news sentiment, and options
    positioning into final_direction, edge_score, unified_confidence, validation,
    and execution_hint. Symbol is NSE ticker without .NS (e.g. RELIANCE).
    """
    req = FuseDecisionRequest(symbol=symbol.strip())
    return _json(_decision.fuse_market_decision(req))


@mcp.tool()
def get_live_price(symbol: str) -> str:
    """Live NSE price snapshot (yfinance intraday bar)."""
    return _json(_market.get_live_price(symbol.strip()))


@mcp.tool()
def generate_signal(symbol: str) -> str:
    """Technical BUY/SELL/HOLD from RSI, MACD, Bollinger."""
    return _json(_signals.generate_signal(symbol.strip()))


@mcp.tool()
def analyze_sentiment(symbol: str) -> str:
    """Keyword sentiment from recent headlines (requires NEWSAPI_KEY)."""
    return _json(_sentiment.analyze_sentiment(symbol.strip()))


@mcp.tool()
def get_options_chain(symbol: str) -> str:
    """Near-term options chain slice (OI by strike)."""
    return _json(_options.get_options_chain(symbol.strip()))


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
