"""Regles initiales de detection explicables."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DetectionWindow:
    current_count: int
    previous_count: int
    baseline_mean: float
    baseline_stddev: float
    current_negative_rate: float
    previous_negative_rate: float
    similar_24h: int
    similar_7d: int


def detect_initial_signals(window: DetectionWindow, *, critical_types: set[str]) -> list[dict[str, object]]:
    signals: list[dict[str, object]] = []
    extra = window.current_count - window.baseline_mean
    if extra >= max(10, 2 * window.baseline_stddev):
        signals.append({"type": "volume_spike", "reason": "ecart >= 2 sigma et +10 mentions"})
    if (
        window.current_count >= 20
        and window.current_negative_rate - window.previous_negative_rate >= 15
    ):
        signals.append({"type": "negative_shift", "reason": "+15 points negatifs avec n >= 20"})
    if window.similar_24h >= 5 or window.similar_7d >= 15:
        signals.append({"type": "recurrence", "reason": "5 mentions/24h ou 15 mentions/7j"})
    for signal_type in sorted(critical_types & {"safety", "fraud", "compliance"}):
        signals.append(
            {
                "type": signal_type,
                "reason": "annotation critique valide; controle humain obligatoire",
                "requires_human_review": True,
            }
        )
    return signals
