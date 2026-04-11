"""Declarative brand monitoring configuration for Discovery Brain V1."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class BrandWatchlist:
    """Configuration used by the planner and budget controller."""

    brand_name: str = "Ramy"
    brand_variants: list[str] = field(
        default_factory=lambda: [
            "ramy",
            "رامي",
            "Ramy Juice",
            "Ramy DZ",
            "ramy dz",
            "jus ramy",
            "عصير رامي",
        ]
    )
    products: list[str] = field(
        default_factory=lambda: [
            "jus",
            "عصير",
            "boisson",
            "eau minerale",
            "nectar",
        ]
    )
    competitors: list[dict[str, object]] = field(
        default_factory=lambda: [
            {"name": "Hamoud Boualem", "variants": ["hamoud", "حمود بوعلام"]},
            {"name": "Ngaous", "variants": ["ngaous", "نقاوس"]},
            {"name": "Ifri", "variants": ["ifri", "إفري"]},
            {"name": "NCA Rouiba", "variants": ["rouiba", "رويبة"]},
        ]
    )
    aspects: list[str] = field(
        default_factory=lambda: [
            "gout",
            "emballage",
            "prix",
            "disponibilite",
            "fraicheur",
        ]
    )
    languages: list[str] = field(default_factory=lambda: ["fr", "ar"])
    priority_domains: list[str] = field(
        default_factory=lambda: [
            "echoroukonline.com",
            "ennaharonline.com",
            "elwatan.com",
            "tsa-algerie.com",
            "liberte-algerie.com",
            "lexpressiondz.com",
            "dzair-tube.dz",
        ]
    )
    monthly_budget_usd: float = 5.0
    budget_split: dict[str, float] = field(
        default_factory=lambda: {
            "press": 0.50,
            "reddit": 0.20,
            "discovery": 0.30,
        }
    )
    recency: dict[str, str] = field(
        default_factory=lambda: {
            "press": "week",
            "reddit": "month",
            "discovery": "month",
        }
    )
