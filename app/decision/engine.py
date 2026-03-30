from __future__ import annotations

from app.decision.schemas import (
    AgreementSummary,
    DecisionWeights,
    Direction,
    MarketDecisionResponse,
    ModuleSource,
    NormalizedSignal,
    ValidationConfig,
    ValidationSummary,
    ReasoningItem,
)


def _direction_sign(d: Direction) -> float:
    if d is Direction.BUY:
        return 1.0
    if d is Direction.SELL:
        return -1.0
    return 0.0


def _final_direction_from_edge(edge: float, min_mag: float) -> Direction:
    if edge > min_mag:
        return Direction.BUY
    if edge < -min_mag:
        return Direction.SELL
    return Direction.NEUTRAL


def _execution_hint(
    final: Direction,
    edge: float,
    unified: float,
    validation: ValidationSummary,
) -> str:
    if validation.rejected or final is Direction.NEUTRAL:
        return "no_trade"
    strength = abs(edge) * unified
    if strength >= 0.45 and unified >= 0.55:
        return "strong_signal"
    if strength >= 0.25:
        return "moderate_signal"
    return "weak_signal"

def build_reasoning(signals: list[NormalizedSignal]) -> list[ReasoningItem]:
    reasoning = []

    for s in signals:
        source = s.source
        direction = s.direction
        confidence = s.confidence

        details = ""

        if source.value == "technical":
            indicators = s.metadata.get("indicators")
            if indicators:
                details = "Technical indicators suggest trend"
            else:
                details = "Technical signal generated"

        elif source.value == "sentiment":
            score = s.metadata.get("sentiment_score")
            count = s.metadata.get("headline_count")
            if score is not None and count is not None:
                details = f"Sentiment score {score} from {count} headlines"
            else:
                details = "Sentiment data unavailable"
        elif source.value == "options":
            pcr = s.metadata.get("put_call_oi_ratio")
            if pcr:
                details = f"PCR = {pcr}"
            else:
                details = "Options activity analyzed"

        reasoning.append(
            ReasoningItem(
                source=source,
                direction=direction,
                confidence=round(confidence, 2),
                details=details,
            )
        )

    return reasoning
class DecisionEngine:
    """
    Rule-based, deterministic fusion of normalized module outputs.
    Designed for interpretability; ML weighting can replace weight application later.
    """

    def fuse(
        self,
        symbol: str,
        signals: list[NormalizedSignal],
        weights: DecisionWeights,
        validation_cfg: ValidationConfig,
        *,
        annualized_volatility: float | None = None,
        volume: int | None = None,
        include_raw: bool = True,
    ) -> MarketDecisionResponse:
        notes: list[str] = []
        if not signals:
            reasoning = build_reasoning(signals)
            return MarketDecisionResponse(
                symbol=symbol,
                final_direction=Direction.NEUTRAL,
                edge_score=0.0,
                unified_confidence=0.0,
                execution_hint="no_trade",
                agreement=AgreementSummary(
                    notes=["No module signals supplied; holding neutral"],
                ),
                validation=ValidationSummary(
                    passed=False,
                    rejected=True,
                    reasons=["empty_signal_set"],
                    annualized_volatility=annualized_volatility,
                    volume=volume,
                ),
                reasoning=reasoning,
                normalized_signals=list(signals) if include_raw else [],
                fusion_notes=notes,
            )

        by_source = {s.source: s for s in signals}
        active_weight_sum = 0.0
        weighted_direction = 0.0
        weighted_conf_sum = 0.0

        for src, sig in by_source.items():
            w = weights.weight_for(src)
            if w <= 0:
                continue
            active_weight_sum += w
            weighted_direction += w * _direction_sign(sig.direction) * sig.confidence
            weighted_conf_sum += w * sig.confidence

        if active_weight_sum <= 0:
            notes.append("All module weights are zero; cannot fuse.")
            edge = 0.0
            raw_conf = 0.0
        else:
            edge = weighted_direction / active_weight_sum
            raw_conf = weighted_conf_sum / active_weight_sum

        agreement = self._agreement(signals, notes)
        if agreement.conflict:
            penalty = 0.15
            raw_conf = max(0.0, raw_conf - penalty)
            notes.append(f"Cross-module conflict detected; confidence haircut {penalty:.2f}")

        unified = max(0.0, min(1.0, raw_conf))
        if agreement.buy_votes >= 2 and agreement.sell_votes == 0:
            unified = min(1.0, unified + 0.05)
            notes.append("Two-way bullish alignment boost (+0.05 cap)")
        if agreement.sell_votes >= 2 and agreement.buy_votes == 0:
            unified = min(1.0, unified + 0.05)
            notes.append("Two-way bearish alignment boost (+0.05 cap)")

        vol_warnings: list[str] = []
        if (
            annualized_volatility is not None
            and annualized_volatility > validation_cfg.high_volatility_annualized
        ):
            cut = validation_cfg.volatility_confidence_penalty
            unified = max(0.0, unified - cut)
            vol_warnings.append(
                f"High realized volatility ({annualized_volatility:.2f}); "
                f"applied -{cut:.2f} to unified confidence"
            )

        val = self._validate(
            validation_cfg,
            edge,
            unified,
            agreement,
            annualized_volatility=annualized_volatility,
            volume=volume,
        )
        val.warnings.extend(vol_warnings)

        final = _final_direction_from_edge(edge, validation_cfg.min_edge_magnitude)
        if val.rejected:
            final = Direction.NEUTRAL

        hint = _execution_hint(final, edge, unified, val)
        reasoning = build_reasoning(signals)
        return MarketDecisionResponse(
            symbol=symbol,
            final_direction=final,
            edge_score=round(edge, 4),
            unified_confidence=round(unified, 4),
            execution_hint=hint,
            agreement=agreement,
            validation=val,
            reasoning=reasoning,
            normalized_signals=list(signals) if include_raw else [],
            fusion_notes=notes,
        )

    def _agreement(self, signals: list[NormalizedSignal], notes: list[str]) -> AgreementSummary:
        buy_votes = sell_votes = neutral_votes = 0
        for s in signals:
            if s.direction is Direction.BUY:
                buy_votes += 1
            elif s.direction is Direction.SELL:
                sell_votes += 1
            else:
                neutral_votes += 1

        conflict = buy_votes > 0 and sell_votes > 0
        if conflict:
            notes.append("Modules disagree on direction (buy vs sell present)")

        return AgreementSummary(
            buy_votes=buy_votes,
            sell_votes=sell_votes,
            neutral_votes=neutral_votes,
            conflict=conflict,
        )

    def _validate(
        self,
        cfg: ValidationConfig,
        edge: float,
        unified: float,
        agreement: AgreementSummary,
        *,
        annualized_volatility: float | None,
        volume: int | None,
    ) -> ValidationSummary:
        reasons: list[str] = []
        warnings: list[str] = []

        if unified < cfg.min_unified_confidence:
            reasons.append("unified_confidence_below_threshold")

        if agreement.conflict and abs(edge) < cfg.min_edge_magnitude:
            reasons.append("conflicting_modules_with_low_edge")

        rejected = bool(reasons)
        passed = not rejected

        if volume is not None and volume < cfg.min_volume_liquidity:
            warnings.append("low_intraday_volume_vs_threshold")

        return ValidationSummary(
            passed=passed,
            rejected=rejected,
            reasons=reasons,
            warnings=warnings,
            annualized_volatility=annualized_volatility,
            volume=volume,
        )
    