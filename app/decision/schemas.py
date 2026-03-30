from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class Direction(str, Enum):
    BUY = "buy"
    SELL = "sell"
    NEUTRAL = "neutral"


class ModuleSource(str, Enum):
    TECHNICAL = "technical"
    SENTIMENT = "sentiment"
    OPTIONS = "options"


class NormalizedSignal(BaseModel):
    """Canonical input for the decision layer (one row per upstream module)."""

    source: ModuleSource
    direction: Direction
    confidence: float = Field(ge=0.0, le=1.0, description="Module self-confidence in [0,1]")
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("confidence")
    @classmethod
    def clamp_confidence(cls, v: float) -> float:
        return max(0.0, min(1.0, float(v)))


class DecisionWeights(BaseModel):
    """Configurable fusion weights (rule-based v1)."""

    technical: float = Field(default=0.45, ge=0.0, le=1.0)
    sentiment: float = Field(default=0.30, ge=0.0, le=1.0)
    options: float = Field(default=0.25, ge=0.0, le=1.0)

    def weight_for(self, source: ModuleSource) -> float:
        return {
            ModuleSource.TECHNICAL: self.technical,
            ModuleSource.SENTIMENT: self.sentiment,
            ModuleSource.OPTIONS: self.options,
        }[source]


class ValidationConfig(BaseModel):
    min_unified_confidence: float = Field(default=0.35, ge=0.0, le=1.0)
    min_edge_magnitude: float = Field(default=0.12, ge=0.0, le=1.0)
    conflict_penalty: float = Field(default=0.15, ge=0.0, le=1.0)
    alignment_boost: float = Field(default=0.05, ge=0.0, le=1.0)
    high_volatility_annualized: float = Field(
        default=0.45,
        ge=0.0,
        le=2.0,
        description="If realized vol (annualized) exceeds this, apply a confidence haircut",
    )
    volatility_confidence_penalty: float = Field(default=0.12, ge=0.0, le=1.0)
    min_volume_liquidity: int = Field(
        default=5_000,
        ge=0,
        description="1m-bar volume threshold (yfinance intraday); below => liquidity warning",
    )


class AgreementSummary(BaseModel):
    buy_votes: int = 0
    sell_votes: int = 0
    neutral_votes: int = 0
    conflict: bool = False
    notes: list[str] = Field(default_factory=list)


class ValidationSummary(BaseModel):
    passed: bool
    rejected: bool
    reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    annualized_volatility: float | None = None
    volume: int | None = None


class FuseDecisionRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    weights: DecisionWeights = Field(default_factory=DecisionWeights)
    validation: ValidationConfig = Field(default_factory=ValidationConfig)
    include_raw_modules: bool = Field(
        default=True,
        description="If true, response includes normalized per-module signals for audit",
    )


class MarketDecisionResponse(BaseModel):
    symbol: str
    final_direction: Direction
    edge_score: float = Field(description="Signed bullish/bearish strength in [-1, 1]")
    unified_confidence: float = Field(ge=0.0, le=1.0)
    execution_hint: str
    agreement: AgreementSummary
    validation: ValidationSummary
    normalized_signals: list[NormalizedSignal] = Field(default_factory=list)
    fusion_notes: list[str] = Field(default_factory=list)


class ManualFuseRequest(BaseModel):
    """Fuse caller-supplied normalized signals (tests / external pipelines)."""

    symbol: str = Field(default="MANUAL")
    signals: list[NormalizedSignal]
    weights: DecisionWeights = Field(default_factory=DecisionWeights)
    validation: ValidationConfig = Field(default_factory=ValidationConfig)
    annualized_volatility: float | None = None
    volume: int | None = None
