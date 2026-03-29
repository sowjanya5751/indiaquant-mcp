import pytest

from app.decision.engine import DecisionEngine
from app.decision.schemas import (
    DecisionWeights,
    Direction,
    ModuleSource,
    NormalizedSignal,
    ValidationConfig,
)


@pytest.fixture
def engine() -> DecisionEngine:
    return DecisionEngine()


def test_aligned_buy_modules_high_confidence(engine: DecisionEngine) -> None:
    signals = [
        NormalizedSignal(
            source=ModuleSource.TECHNICAL,
            direction=Direction.BUY,
            confidence=0.9,
        ),
        NormalizedSignal(
            source=ModuleSource.SENTIMENT,
            direction=Direction.BUY,
            confidence=0.8,
        ),
        NormalizedSignal(
            source=ModuleSource.OPTIONS,
            direction=Direction.BUY,
            confidence=0.7,
        ),
    ]
    out = engine.fuse(
        "TEST",
        signals,
        DecisionWeights(),
        ValidationConfig(min_unified_confidence=0.2, min_edge_magnitude=0.1),
    )
    assert out.final_direction is Direction.BUY
    assert out.edge_score > 0.4
    assert out.unified_confidence > 0.5
    assert out.agreement.conflict is False
    assert out.validation.rejected is False


def test_conflict_reduces_confidence(engine: DecisionEngine) -> None:
    signals = [
        NormalizedSignal(
            source=ModuleSource.TECHNICAL,
            direction=Direction.BUY,
            confidence=0.9,
        ),
        NormalizedSignal(
            source=ModuleSource.SENTIMENT,
            direction=Direction.SELL,
            confidence=0.9,
        ),
        NormalizedSignal(
            source=ModuleSource.OPTIONS,
            direction=Direction.NEUTRAL,
            confidence=0.5,
        ),
    ]
    out = engine.fuse(
        "TEST",
        signals,
        DecisionWeights(),
        ValidationConfig(),
    )
    assert out.agreement.conflict is True
    assert "Cross-module conflict" in " ".join(out.fusion_notes)


def test_low_confidence_rejection(engine: DecisionEngine) -> None:
    signals = [
        NormalizedSignal(
            source=ModuleSource.TECHNICAL,
            direction=Direction.BUY,
            confidence=0.2,
        ),
        NormalizedSignal(
            source=ModuleSource.SENTIMENT,
            direction=Direction.NEUTRAL,
            confidence=0.2,
        ),
        NormalizedSignal(
            source=ModuleSource.OPTIONS,
            direction=Direction.NEUTRAL,
            confidence=0.2,
        ),
    ]
    out = engine.fuse(
        "TEST",
        signals,
        DecisionWeights(),
        ValidationConfig(min_unified_confidence=0.5),
    )
    assert out.validation.rejected is True
    assert out.final_direction is Direction.NEUTRAL


def test_empty_signals(engine: DecisionEngine) -> None:
    out = engine.fuse("X", [], DecisionWeights(), ValidationConfig())
    assert out.validation.rejected is True
    assert out.final_direction is Direction.NEUTRAL


def test_normalize_technical_error_fallback() -> None:
    from app.decision.normalizers import normalize_technical

    s = normalize_technical({"error": "No data"})
    assert s is not None
    assert s.source == ModuleSource.TECHNICAL
    assert s.direction is Direction.NEUTRAL
