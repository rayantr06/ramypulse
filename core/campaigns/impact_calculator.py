"""Calculateur d'impact de campagne RamyPulse.

Implémente les trois fenêtres pré/active/post et le score d'attribution.
Signatures conformes à INTERFACES.md Section 4.1.
"""

from __future__ import annotations

import logging
from datetime import timedelta

import pandas as pd

from config import DEFAULT_POST_WINDOW_DAYS, DEFAULT_PRE_WINDOW_DAYS, MIN_SIGNALS_FOR_ATTRIBUTION
from core.campaigns.campaign_manager import get_campaign

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Fonctions de filtrage
# ---------------------------------------------------------------------------


def filter_signals_for_campaign(
    df: pd.DataFrame,
    campaign: dict,
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    """Filtre le DataFrame selon les dimensions de la campagne dans une fenêtre temporelle.

    Filtres appliqués (AND logique, champ ignoré si None/vide) :
    - timestamp entre start_date et end_date
    - channel == campaign["platform"] (si platform != "multi_platform")
    - aspect in campaign["target_aspects"] (si non vide)
    - wilaya in campaign["target_regions"] (si non vide)
    - text contient au moins 1 keyword de campaign["keywords"] (si non vide)

    Returns: DataFrame filtré, peut être vide.
    """
    if df.empty:
        return df.copy()

    try:
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
    except Exception:
        logger.warning("Dates invalides dans filter_signals_for_campaign : %s / %s", start_date, end_date)
        return pd.DataFrame()

    result = df.copy()

    # Filtre temporel
    if "timestamp" in result.columns:
        ts = pd.to_datetime(result["timestamp"], errors="coerce")
        result = result[ts.between(start_dt, end_dt)]

    if result.empty:
        return result

    # Filtre platform (channel)
    platform = campaign.get("platform")
    if platform and platform != "multi_platform" and "channel" in result.columns:
        result = result[result["channel"] == platform]

    if result.empty:
        return result

    # Filtre aspects
    target_aspects = campaign.get("target_aspects") or []
    if target_aspects and "aspect" in result.columns:
        result = result[result["aspect"].isin(target_aspects)]

    if result.empty:
        return result

    # Filtre wilayas
    target_regions = campaign.get("target_regions") or []
    if target_regions and "wilaya" in result.columns:
        result = result[result["wilaya"].isin(target_regions)]

    if result.empty:
        return result

    # Filtre keywords dans le texte
    keywords = campaign.get("keywords") or []
    if keywords and "text" in result.columns:
        kw_lower = [k.lower() for k in keywords]
        mask = result["text"].apply(
            lambda t: any(kw in str(t).lower() for kw in kw_lower) if pd.notna(t) else False
        )
        result = result[mask]

    return result


# ---------------------------------------------------------------------------
# Calculs de métriques NSS
# ---------------------------------------------------------------------------


def _compute_nss(df: pd.DataFrame) -> float | None:
    """Calcule le NSS sur un DataFrame de signaux."""
    if df.empty or "sentiment_label" not in df.columns:
        return None
    total = len(df)
    if total == 0:
        return None
    pos = int(df["sentiment_label"].isin(["très_positif", "positif"]).sum())
    neg = int(df["sentiment_label"].isin(["très_négatif", "négatif"]).sum())
    return round((pos - neg) / total * 100, 2)


def _aspect_breakdown(df: pd.DataFrame) -> dict:
    """Calcule le NSS par aspect sur un DataFrame."""
    if df.empty or "aspect" not in df.columns:
        return {}
    result = {}
    for aspect in df["aspect"].dropna().unique():
        if not aspect:
            continue
        sub = df[df["aspect"] == aspect]
        nss = _compute_nss(sub)
        if nss is not None:
            result[str(aspect)] = nss
    return result


def _sentiment_breakdown(df: pd.DataFrame) -> dict:
    """Compte les occurrences de chaque label de sentiment."""
    labels = ["très_positif", "positif", "neutre", "négatif", "très_négatif"]
    if df.empty or "sentiment_label" not in df.columns:
        return {label: 0 for label in labels}
    counts = df["sentiment_label"].value_counts()
    return {label: int(counts.get(label, 0)) for label in labels}


def _phase_metrics(df: pd.DataFrame) -> dict:
    """Calcule les métriques (nss, volume, breakdowns) pour une phase."""
    return {
        "nss": _compute_nss(df),
        "volume": len(df),
        "aspect_breakdown": _aspect_breakdown(df),
        "sentiment_breakdown": _sentiment_breakdown(df),
    }


# ---------------------------------------------------------------------------
# Calcul d'impact global
# ---------------------------------------------------------------------------


def compute_campaign_impact(
    campaign_id: str,
    df_annotated: pd.DataFrame,
) -> dict:
    """Calcule l'impact d'une campagne sur les métriques NSS (3 fenêtres).

    Returns dict conforme à INTERFACES.md Section 4.1.
    """
    _empty_phase = {"nss": None, "volume": 0, "aspect_breakdown": {}, "sentiment_breakdown": {}}

    campaign = get_campaign(campaign_id)
    if campaign is None:
        logger.warning("Campagne introuvable : %s", campaign_id)
        return {
            "campaign_id": campaign_id,
            "campaign_name": None,
            "phases": {"pre": dict(_empty_phase), "active": dict(_empty_phase), "post": dict(_empty_phase)},
            "uplift_nss": None,
            "uplift_volume_pct": None,
            "is_reliable": False,
            "reliability_note": "Campagne introuvable",
        }

    start_date = campaign.get("start_date")
    end_date = campaign.get("end_date")
    pre_window = int(campaign.get("pre_window_days") or DEFAULT_PRE_WINDOW_DAYS)
    post_window = int(campaign.get("post_window_days") or DEFAULT_POST_WINDOW_DAYS)

    # Calcul des bornes temporelles de chaque fenêtre
    if start_date:
        start_dt = pd.to_datetime(start_date)
        pre_start = (start_dt - timedelta(days=pre_window)).strftime("%Y-%m-%d")
        pre_end = start_date
    else:
        pre_start = pre_end = None

    if end_date:
        end_dt = pd.to_datetime(end_date)
        post_start = end_date
        post_end = (end_dt + timedelta(days=post_window)).strftime("%Y-%m-%d")
    else:
        post_start = post_end = None

    # Filtrage par fenêtre
    if df_annotated.empty:
        df_pre = df_active = df_post = pd.DataFrame()
    else:
        df_pre = (
            filter_signals_for_campaign(df_annotated, campaign, pre_start, pre_end)
            if pre_start and pre_end else pd.DataFrame()
        )
        df_active = (
            filter_signals_for_campaign(df_annotated, campaign, start_date, end_date)
            if start_date and end_date else pd.DataFrame()
        )
        df_post = (
            filter_signals_for_campaign(df_annotated, campaign, post_start, post_end)
            if post_start and post_end else pd.DataFrame()
        )

    phases = {
        "pre": _phase_metrics(df_pre),
        "active": _phase_metrics(df_active),
        "post": _phase_metrics(df_post),
    }

    pre_nss = phases["pre"]["nss"]
    post_nss = phases["post"]["nss"]
    pre_vol = phases["pre"]["volume"]
    post_vol = phases["post"]["volume"]

    uplift_nss: float | None = None
    if pre_nss is not None and post_nss is not None:
        uplift_nss = round(post_nss - pre_nss, 2)

    uplift_volume_pct: float | None = None
    if pre_vol > 0:
        uplift_volume_pct = round((post_vol - pre_vol) / pre_vol * 100, 2)

    is_reliable = (
        phases["pre"]["volume"] >= MIN_SIGNALS_FOR_ATTRIBUTION
        and phases["active"]["volume"] >= MIN_SIGNALS_FOR_ATTRIBUTION
        and phases["post"]["volume"] >= MIN_SIGNALS_FOR_ATTRIBUTION
    )
    reliability_note = (
        ""
        if is_reliable
        else f"Volume insuffisant pour une attribution fiable (minimum {MIN_SIGNALS_FOR_ATTRIBUTION} signaux par phase)"
    )

    return {
        "campaign_id": campaign_id,
        "campaign_name": campaign.get("campaign_name"),
        "phases": phases,
        "uplift_nss": uplift_nss,
        "uplift_volume_pct": uplift_volume_pct,
        "is_reliable": is_reliable,
        "reliability_note": reliability_note,
    }


# ---------------------------------------------------------------------------
# Score d'attribution individuel
# ---------------------------------------------------------------------------


def compute_attribution_score(row: pd.Series, campaign: dict) -> float:
    """Calcule le score d'attribution d'un signal à une campagne (0.0 à 1.0).

    Logique :
    - Base (fenêtre temporelle + plateforme) : 0.3
    - Handle influenceur mentionné dans text : +0.4
    - >= 1 keyword présent dans text : +0.2 (max)
    - aspect correspond à target_aspects : +0.1
    """
    score = 0.3  # Score de base : signal dans la fenêtre temporelle + plateforme

    text = str(row.get("text", "")).lower()

    # Handle influenceur
    handle = campaign.get("influencer_handle")
    if handle and str(handle).lower() in text:
        score += 0.4

    # Keywords
    keywords = campaign.get("keywords") or []
    if keywords and any(str(kw).lower() in text for kw in keywords):
        score += 0.2

    # Aspect
    target_aspects = campaign.get("target_aspects") or []
    row_aspect = row.get("aspect", "")
    if target_aspects and row_aspect in target_aspects:
        score += 0.1

    return min(round(score, 2), 1.0)
