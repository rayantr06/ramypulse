"""KPI transparents et cohorte analytique LIDAL Pulse V3."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from statistics import median
from typing import Iterable, Mapping


ELIGIBLE_SENTIMENTS = {"positif", "negatif", "neutre", "mixte"}


def is_eligible_mention(row: Mapping[str, object], *, consumer_only: bool) -> bool:
    """Applique le contrat de cohorte, sans reclasser le contenu."""
    if row.get("validation_status") != "valid":
        return False
    if not bool(row.get("is_exploitable")):
        return False
    if row.get("business_relevance") == "aucune":
        return False
    if bool(row.get("requires_parent_context")):
        return False
    if consumer_only and row.get("author_role") != "consommateur":
        return False
    return str(row.get("sentiment")) in ELIGIBLE_SENTIMENTS


def sentiment_net(counts: Mapping[str, int]) -> float | None:
    total = sum(max(0, int(counts.get(label, 0))) for label in ELIGIBLE_SENTIMENTS)
    if total < 30:
        return None
    return round(100 * (int(counts.get("positif", 0)) - int(counts.get("negatif", 0))) / total, 1)


@dataclass(frozen=True)
class OverviewInput:
    mentions: list[Mapping[str, object]]
    previous_mentions: list[Mapping[str, object]]
    collected_documents: int
    valid_annotations: int
    open_signals: list[Mapping[str, object]]
    ownership_delays_hours: list[float]
    overdue_actions: int
    source_health: list[Mapping[str, object]]


def build_overview(data: OverviewInput, *, consumer_only: bool = True) -> dict[str, object]:
    current = [row for row in data.mentions if is_eligible_mention(row, consumer_only=consumer_only)]
    previous = [
        row for row in data.previous_mentions if is_eligible_mention(row, consumer_only=consumer_only)
    ]
    counts = Counter(str(row["sentiment"]) for row in current)
    previous_counts = Counter(str(row["sentiment"]) for row in previous)
    current_net = sentiment_net(counts)
    previous_net = sentiment_net(previous_counts)
    delta = None if current_net is None or previous_net is None else round(current_net - previous_net, 1)
    qualified = len(current)
    coverage = (
        round(100 * data.valid_annotations / data.collected_documents, 1)
        if data.collected_documents > 0
        else 0.0
    )
    severities = Counter(str(row.get("severity", "low")) for row in data.open_signals)
    aspect_current = Counter(
        aspect
        for row in current
        for aspect in row.get("aspects", [])
        if isinstance(aspect, str)
    )
    aspect_previous = Counter(
        aspect
        for row in previous
        for aspect in row.get("aspects", [])
        if isinstance(aspect, str)
    )
    drivers = []
    for aspect, mention_count in aspect_current.most_common(5):
        current_share = 100 * mention_count / max(qualified, 1)
        previous_share = 100 * aspect_previous[aspect] / max(len(previous), 1)
        drivers.append(
            {
                "aspect": aspect,
                "delta_points": round(current_share - previous_share, 1),
                "mention_count": mention_count,
            }
        )
    return {
        "qualified_mentions": qualified,
        "collected_documents": data.collected_documents,
        "valid_annotations": data.valid_annotations,
        "analytical_coverage_percent": coverage,
        "net_sentiment": current_net,
        "net_sentiment_delta": delta,
        "insufficient_sample": qualified < 30,
        "distribution": {label: counts[label] for label in ("positif", "negatif", "neutre", "mixte")},
        "negative_rate_percent": round(100 * counts["negatif"] / qualified, 1) if qualified else 0.0,
        "open_signals_by_severity": {
            label: severities[label] for label in ("critical", "high", "medium", "low")
        },
        "median_time_to_ownership_hours": (
            round(median(data.ownership_delays_hours), 1) if data.ownership_delays_hours else None
        ),
        "overdue_actions": data.overdue_actions,
        "top_drivers": drivers,
        "source_health": data.source_health,
    }


def priority_score(
    *,
    severity: float | None,
    velocity: float | None,
    volume: float | None,
    reach: float | None,
    confidence: float | None,
) -> tuple[float, list[dict[str, float | str]]]:
    """Score deterministe avec renormalisation des poids manquants."""
    values = {
        "gravite": (severity, 0.35),
        "vitesse": (velocity, 0.20),
        "volume": (volume, 0.20),
        "portee": (reach, 0.10),
        "confiance": (confidence, 0.15),
    }
    available = {key: value for key, value in values.items() if value[0] is not None}
    weight_total = sum(weight for _, weight in available.values())
    if weight_total == 0:
        return 0.0, []
    factors = []
    score = 0.0
    for label, (value, weight) in available.items():
        normalized_weight = weight / weight_total
        bounded_value = min(100.0, max(0.0, float(value)))
        score += bounded_value * normalized_weight
        factors.append({"label": label, "value": bounded_value, "weight": round(normalized_weight, 4)})
    return round(score, 1), factors
