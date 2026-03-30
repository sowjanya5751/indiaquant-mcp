from __future__ import annotations

from typing import Any

from app.decision.schemas import Direction, ModuleSource, NormalizedSignal


def normalize_technical(raw: dict[str, Any]) -> NormalizedSignal | None:
    if raw.get("error"):
        return NormalizedSignal(
            source=ModuleSource.TECHNICAL,
            direction=Direction.NEUTRAL,
            confidence=0.12,
            metadata={"error": raw.get("error")},
        )
    sig = str(raw.get("signal", "HOLD")).upper()
    conf_raw = float(raw.get("confidence", 0) or 0)
    confidence = max(0.0, min(1.0, conf_raw / 100.0))

    if sig == "BUY":
        direction = Direction.BUY
    elif sig == "SELL":
        direction = Direction.SELL
    else:
        direction = Direction.NEUTRAL
        confidence = max(confidence, 0.25)

    return NormalizedSignal(
        source=ModuleSource.TECHNICAL,
        direction=direction,
        confidence=confidence,
        metadata={
            "raw_signal": sig,
            "indicators": raw.get("indicators"),
        },
    )


def normalize_sentiment(raw: dict[str, Any]) -> NormalizedSignal | None:
    if raw.get("error"):
        return NormalizedSignal(
            source=ModuleSource.SENTIMENT,
            direction=Direction.NEUTRAL,
            confidence=0.1,
            metadata={"error": raw.get("error")},
        )
    label = str(raw.get("signal", "NEUTRAL")).upper()
    score = int(raw.get("sentiment_score", 0) or 0)

    if label == "POSITIVE":
        direction = Direction.BUY
        confidence = min(1.0, 0.35 + abs(score) * 0.08)
    elif label == "NEGATIVE":
        direction = Direction.SELL
        confidence = min(1.0, 0.35 + abs(score) * 0.08)
    else:
        direction = Direction.NEUTRAL
        confidence = max(0.2, 0.5 - min(3, abs(score)) * 0.08)

    return NormalizedSignal(
        source=ModuleSource.SENTIMENT,
        direction=direction,
        confidence=confidence,
        metadata={
            "sentiment_score": score,
            "headline_count": len(raw.get("headlines") or []),
        },
    )


def normalize_options(
    chain: dict[str, Any],
    *,
    spot_price: float | None = None,
    max_pain: float | None = None,
) -> NormalizedSignal | None:
    if chain.get("error"):
        return NormalizedSignal(
            source=ModuleSource.OPTIONS,
            direction=Direction.NEUTRAL,
            confidence=0.12,
            metadata={"error": chain.get("error")},
        )
    rows = chain.get("options") or []
    if not rows:
        return NormalizedSignal(
            source=ModuleSource.OPTIONS,
            direction=Direction.NEUTRAL,
            confidence=0.2,
            metadata={"reason": "empty_options_slice"},
        )

    total_call_oi = sum(int(r.get("call_oi", 0) or 0) for r in rows)
    total_put_oi = sum(int(r.get("put_oi", 0) or 0) for r in rows)
    denom = max(total_call_oi, 1)
    pcr = total_put_oi / denom

    direction = Direction.NEUTRAL
    confidence = 0.35
    notes: list[str] = []

    if pcr > 1.2:
        direction = Direction.SELL
        confidence = min(0.85, 0.4 + min(0.45, (pcr - 1.2) * 0.35))
        notes.append("elevated_put_call_oi_ratio")
    elif pcr < 0.75:
        direction = Direction.BUY
        confidence = min(0.85, 0.4 + min(0.45, (0.75 - pcr) * 0.35))
        notes.append("depressed_put_call_oi_ratio")
    else:
        notes.append("pcr_near_balanced")

    if spot_price is not None and max_pain is not None and max_pain > 0:
        diff_pct = (spot_price - max_pain) / max_pain
        notes.append(f"spot_vs_max_pain_pct={diff_pct:.4f}")
        if abs(diff_pct) > 0.02:
            pain_bias = Direction.SELL if diff_pct > 0 else Direction.BUY
            if pain_bias is direction or direction is Direction.NEUTRAL:
                direction = pain_bias
                confidence = min(1.0, confidence + 0.08)
            else:
                confidence = max(0.2, confidence - 0.1)
                notes.append("max_pain_tension_vs_pcr")

    return NormalizedSignal(
        source=ModuleSource.OPTIONS,
        direction=direction,
        confidence=confidence,
        metadata={
            "put_call_oi_ratio": round(pcr, 4),
            "total_call_oi": total_call_oi,
            "total_put_oi": total_put_oi,
            "expiry": chain.get("expiry"),
            "max_pain": max_pain,
            "spot": spot_price,
            "notes": notes,
        },
    )
