"""Fonctions helper testables pour la page What-If.

Logique métier extraite de la page Streamlit pour permettre le TDD.
"""
import logging
from datetime import datetime

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Classification NSS
# ---------------------------------------------------------------------------

def nss_label(nss: float) -> str:
    """Retourne le libellé qualitatif d'un score NSS.

    Seuils PRD :
      > 50  → Excellent
      20-50 → Bon
      0-20  → Neutre
      ≤ 0   → Problématique

    Args:
        nss: Valeur du Net Sentiment Score.

    Returns:
        Libellé texte correspondant.
    """
    if nss > 50:
        return "Excellent"
    if nss > 20:
        return "Bon"
    if nss > 0:
        return "Neutre"
    return "Problématique"


# ---------------------------------------------------------------------------
# Couleurs et flèches delta
# ---------------------------------------------------------------------------

def delta_color(delta: float) -> str:
    """Retourne la couleur hex associée au signe du delta.

    Args:
        delta: Variation du NSS.

    Returns:
        Hex vert (#2ecc71), rouge (#e74c3c) ou gris (#95a5a6).
    """
    if delta > 0:
        return "#2ecc71"
    if delta < 0:
        return "#e74c3c"
    return "#95a5a6"


def delta_arrow(delta: float) -> str:
    """Retourne la flèche directionnelle associée au delta.

    Args:
        delta: Variation du NSS.

    Returns:
        '↑', '↓' ou '→'.
    """
    if delta > 0:
        return "↑"
    if delta < 0:
        return "↓"
    return "→"


# ---------------------------------------------------------------------------
# Données pour le chart comparatif par canal
# ---------------------------------------------------------------------------

def build_comparison_chart_data(
    nss_avant: dict[str, float],
    nss_apres: dict[str, float],
) -> pd.DataFrame:
    """Construit un DataFrame long pour un bar chart groupé Plotly.

    Chaque canal apparaît deux fois (Actuel / Simulé).

    Args:
        nss_avant: Dict {canal: nss_actuel}.
        nss_apres: Dict {canal: nss_simulé}.

    Returns:
        DataFrame avec colonnes Canal, NSS, Période.
    """
    rows: list[dict] = []
    canaux = sorted(set(nss_avant) | set(nss_apres))
    for canal in canaux:
        rows.append({"Canal": canal, "NSS": nss_avant.get(canal, 0.0), "Période": "Actuel"})
        rows.append({"Canal": canal, "NSS": nss_apres.get(canal, 0.0), "Période": "Simulé"})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Mock DataFrame (quand aucune donnée ABSA n'est disponible)
# ---------------------------------------------------------------------------

def build_mock_df(n: int = 200) -> pd.DataFrame:
    """Génère un DataFrame ABSA synthétique pour le mode démo.

    Couvre les 5 aspects, 5 sentiments et 4 canaux du standard RamyPulse.

    Args:
        n: Nombre d'enregistrements à générer.

    Returns:
        DataFrame avec les 7 colonnes standard.
    """
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
            "timestamp": [datetime(2024, 1, 1).isoformat()] * n,
            "confidence": rng.uniform(0.6, 1.0, n).round(3).tolist(),
        }
    )
