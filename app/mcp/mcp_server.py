from fastapi import FastAPI
from pydantic import BaseModel

from app.market_data.market_data_service import MarketDataService
from app.signals.signal_service import SignalEngine
from app.options.options_service import OptionsAnalyzer
from app.analytics.greeks_calculator import GreeksCalculator
from app.portfolio.portfolio_service import PortfolioService
from app.analytics.market_scanner import MarketScanner
from app.analytics.sentiment_service import SentimentAnalyzer
from app.analytics.sector_heatmap import SectorHeatmap
from app.models.request_models import SymbolRequest, TradeRequest

app = FastAPI(title="IndiaQuant MCP Server")

market = MarketDataService()
signals = SignalEngine()
options = OptionsAnalyzer()
greeks = GreeksCalculator()
portfolio = PortfolioService()
scanner = MarketScanner()
sentiment = SentimentAnalyzer()
heatmap = SectorHeatmap()

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
        "docs": "/docs"
    }

@app.post("/detect_unusual_activity")
def detect_unusual_activity(request: SymbolRequest):

    return options.detect_unusual_activity(request.symbol)

@app.get("/get_sector_heatmap")
def get_sector_heatmap():

    return heatmap.get_sector_heatmap()