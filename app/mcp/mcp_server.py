from fastapi import FastAPI

from app.market_data.market_data_service import MarketDataService
from app.signals.signal_service import SignalEngine
from app.options.options_service import OptionsAnalyzer
from app.analytics.greeks_calculator import GreeksCalculator
from app.portfolio.portfolio_service import PortfolioService
from app.analytics.market_scanner import MarketScanner
from app.analytics.sentiment_service import SentimentAnalyzer
from app.analytics.sector_heatmap import SectorHeatmap
from app.models.request_models import SymbolRequest, TradeRequest
from app.decision.schemas import (
    DecisionWeights,
    FuseDecisionRequest,
    ManualFuseRequest,
    MarketDecisionResponse,
    NormalizedSignal,
    ValidationConfig,
)
from app.decision.service import DecisionLayerService

app = FastAPI(title="IndiaQuant MCP Server")

market = MarketDataService()
signals = SignalEngine()
options = OptionsAnalyzer()
greeks = GreeksCalculator()
portfolio = PortfolioService()
scanner = MarketScanner()
sentiment = SentimentAnalyzer()
heatmap = SectorHeatmap()
decision_layer = DecisionLayerService(
    signals_engine=signals,
    options=options,
    sentiment_analyzer=sentiment,
)

@app.post("/get_live_price")
def get_live_price(request: SymbolRequest):

    return market.get_live_price(request.symbol)

@app.post("/generate_signal")
def generate_signal(request: SymbolRequest):
    return signals.generate_signal(request.symbol)

@app.post("/get_options_chain")
def get_options_chain(req: SymbolRequest):
    return options.get_options_chain(req.symbol)

@app.post("/calculate_greeks")
def calculate_greeks():
    return greeks.calculate_greeks(
        S=200,
        K=210,
        T=30/365,
        r=0.05,
        sigma=0.2
    )

@app.post("/place_virtual_trade")
def place_trade(request: TradeRequest):

    return portfolio.place_trade(
        request.symbol,
        request.qty,
        request.side
    )

@app.get("/get_portfolio_pnl")
def get_pnl():
    return portfolio.get_portfolio_pnl()

@app.get("/scan_market")
def scan_market():
    symbols = ["AAPL", "TSLA", "MSFT", "GOOG"]
    return scanner.scan_market(symbols)

@app.get("/")
def root():
    return {
        "message": "IndiaQuant MCP Server running",
        "docs": "/docs",
        "decision_layer_v1": {
            "description": "Rule-based fusion of technical + sentiment + options",
            "endpoints": [
                "POST /fuse_market_decision",
                "POST /fuse_decision_manual",
                "GET /schemas/decision_layer",
            ],
            "spec": "docs/decision_layer_first_draft.md",
        },
        "mcp_stdio": {
            "module": "app.mcp.stdio_server",
            "command": "PYTHONPATH=. python3 -m app.mcp.stdio_server",
            "note": "Native MCP (Claude Desktop / Cursor); see README",
        },
    }


@app.get("/schemas/decision_layer")
def decision_layer_json_schemas():
    """JSON Schema exports for non-Python integrators and contract tests."""
    return {
        "json_schema_draft": "https://json-schema.org/draft/2020-12/schema",
        "models": {
            "NormalizedSignal": NormalizedSignal.model_json_schema(),
            "DecisionWeights": DecisionWeights.model_json_schema(),
            "ValidationConfig": ValidationConfig.model_json_schema(),
            "FuseDecisionRequest": FuseDecisionRequest.model_json_schema(),
            "ManualFuseRequest": ManualFuseRequest.model_json_schema(),
            "MarketDecisionResponse": MarketDecisionResponse.model_json_schema(),
        },
    }

@app.post("/detect_unusual_activity")
def detect_unusual_activity(request: SymbolRequest):

    return options.detect_unusual_activity(request.symbol)

@app.get("/get_sector_heatmap")
def get_sector_heatmap():

    return heatmap.get_sector_heatmap()


@app.post("/analyze_sentiment")
def analyze_sentiment_endpoint(request: SymbolRequest):
    return sentiment.analyze_sentiment(request.symbol)


@app.post("/fuse_market_decision", response_model=MarketDecisionResponse)
def fuse_market_decision(request: FuseDecisionRequest) -> MarketDecisionResponse:
    """
    Decision layer v1: normalizes technical, sentiment, and options outputs,
    fuses them with configurable weights, and applies lightweight validation.
    """
    return decision_layer.fuse_market_decision(request)


@app.post("/fuse_decision_manual", response_model=MarketDecisionResponse)
def fuse_decision_manual(request: ManualFuseRequest) -> MarketDecisionResponse:
    """Fuse caller-supplied normalized signals (integration tests / custom pipelines)."""
    return decision_layer.fuse_manual(request)