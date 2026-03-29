from __future__ import annotations

import math
from typing import Any

import yfinance as yf

from app.decision.engine import DecisionEngine
from app.decision.normalizers import (
    normalize_options,
    normalize_sentiment,
    normalize_technical,
)
from app.decision.schemas import (
    FuseDecisionRequest,
    ManualFuseRequest,
    MarketDecisionResponse,
    ModuleSource,
    NormalizedSignal,
)
from app.options.options_service import OptionsAnalyzer
from app.signals.signal_service import SignalEngine


def _nse_ticker(symbol: str) -> str:
    s = symbol.strip().upper()
    if s.endswith(".NS") or s.startswith("^"):
        return s
    return f"{s}.NS"


def _annualized_volatility(symbol: str) -> float | None:
    try:
        t = yf.Ticker(_nse_ticker(symbol))
        hist = t.history(period="3mo")
        if hist.empty or len(hist) < 10:
            return None
        closes = hist["Close"].pct_change().dropna()
        if closes.empty:
            return None
        daily_vol = float(closes.std())
        return float(daily_vol * math.sqrt(252))
    except Exception:
        return None


class DecisionLayerService:
    """
    Orchestrates existing IndiaQuant modules into normalized inputs and fused output.
    """

    def __init__(
        self,
        *,
        signals_engine: SignalEngine | None = None,
        options: OptionsAnalyzer | None = None,
        sentiment_analyzer: Any | None = None,
    ) -> None:
        self.signals = signals_engine or SignalEngine()
        self.options = options or OptionsAnalyzer()
        self.sentiment = sentiment_analyzer
        self.engine = DecisionEngine()

    def fuse_market_decision(self, req: FuseDecisionRequest) -> MarketDecisionResponse:
        sym = req.symbol.strip()
        normalized: list[NormalizedSignal] = []

        tech = normalize_technical(self.signals.generate_signal(sym))
        normalized.append(tech)

        if self.sentiment is not None:
            try:
                normalized.append(normalize_sentiment(self.sentiment.analyze_sentiment(sym)))
            except Exception as exc:
                normalized.append(
                    NormalizedSignal(
                        source=ModuleSource.SENTIMENT,
                        direction=Direction.NEUTRAL,
                        confidence=0.15,
                        metadata={"error": "sentiment_unavailable", "detail": str(exc)[:200]},
                    )
                )
        else:
            normalized.append(
                NormalizedSignal(
                    source=ModuleSource.SENTIMENT,
                    direction=Direction.NEUTRAL,
                    confidence=0.1,
                    metadata={"reason": "sentiment_disabled_no_client"},
                )
            )

        chain = self.options.get_options_chain(sym)
        mp_raw = self.options.calculate_max_pain(sym)
        spot: float | None = None
        max_pain: float | None = None
        if not mp_raw.get("error"):
            max_pain = float(mp_raw["max_pain"])
        try:
            t = yf.Ticker(_nse_ticker(sym))
            h = t.history(period="5d")
            if not h.empty:
                spot = float(h["Close"].iloc[-1])
        except Exception:
            spot = None

        normalized.append(normalize_options(chain, spot_price=spot, max_pain=max_pain))

        vol = _annualized_volatility(sym)
        volume: int | None = None
        try:
            t = yf.Ticker(_nse_ticker(sym))
            intraday = t.history(period="1d", interval="1m")
            if not intraday.empty:
                volume = int(intraday.iloc[-1]["Volume"])
        except Exception:
            volume = None

        return self.engine.fuse(
            sym,
            normalized,
            req.weights,
            req.validation,
            annualized_volatility=vol,
            volume=volume,
            include_raw=req.include_raw_modules,
        )

    def fuse_manual(self, req: ManualFuseRequest) -> MarketDecisionResponse:
        return self.engine.fuse(
            req.symbol,
            req.signals,
            req.weights,
            req.validation,
            annualized_volatility=req.annualized_volatility,
            volume=req.volume,
            include_raw=True,
        )
