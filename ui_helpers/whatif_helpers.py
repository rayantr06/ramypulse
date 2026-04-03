"""Fonctions helper testables pour la page What-If."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def nss_label(nss: float) -> str:
    """Retourne le libelle qualitatif d'un score NSS."""
    if nss > 50:
        return "Excellent"
    if nss > 20:
        return "Bon"
    if nss > 0:
        return "Neutre"
    return "Problématique"


def delta_color(delta: float) -> str:
    """Retourne la couleur hex associee au signe du delta."""
    if delta > 0:
        return "#2ecc71"
    if delta < 0:
        return "#e74c3c"
    return "#95a5a6"


def delta_arrow(delta: float) -> str:
    """Retourne la fleche directionnelle associee au delta."""
    if delta > 0:
        return "↑"
    if delta < 0:
        return "↓"
    return "→"


def build_comparison_chart_data(
    nss_avant: dict[str, float],
    nss_apres: dict[str, float],
) -> pd.DataFrame:
    """Construit un DataFrame long pour un bar chart groupe Plotly."""
    rows: list[dict] = []
    canaux = sorted(set(nss_avant) | set(nss_apres))
    for canal in canaux:
        rows.append({"Canal": canal, "NSS": nss_avant.get(canal, 0.0), "Période": "Actuel"})
        rows.append({"Canal": canal, "NSS": nss_apres.get(canal, 0.0), "Période": "Simulé"})
    return pd.DataFrame(rows)


def build_mock_df(n: int = 200) -> pd.DataFrame:
    """Genere un DataFrame ABSA synthetique pour le mode demo."""
    rng = np.random.default_rng(42)
    sentiments = ["très_positif", "positif", "neutre", "négatif", "très_négatif"]
    aspects = ["goût", "emballage", "prix", "disponibilité", "fraîcheur"]
    canaux = ["facebook", "google_maps", "audio", "youtube"]

    return pd.DataFrame(
        {
            "text": [f"Avis synthétique #{i}" for i in range(n)],
            "sentiment_label": rng.choice(sentiments, n).tolist(),
            "channel": rng.choice(canaux, n).tolist(),
            "aspect": rng.choice(aspects, n).tolist(),
            "source_url": [f"http://demo/{i}" for i in range(n)],
            "timestamp": [
                (datetime(2024, 1, 1) + timedelta(days=int(d))).isoformat()
                for d in rng.integers(0, 56, n)
            ],
            "confidence": rng.uniform(0.6, 1.0, n).round(3).tolist(),
        }
    )
