"""Pre-remplissage de campagne depuis une recommandation."""

from __future__ import annotations

from datetime import date, timedelta
import math

import pandas as pd


def build_campaign_prefill_from_recommendation_record(
    recommendation_record: dict,
    *,
    today: date | None = None,
) -> dict:
    """Construit un dictionnaire de pre-remplissage du formulaire campagne."""
    recommendations = recommendation_record.get("recommendations") or []
    first = recommendations[0] if recommendations else {}
    content = first.get("content") or {}
    influencer_profile = first.get("influencer_profile") or {}
    timing = first.get("timing") or {}
    today_value = today or date.today()

    key_messages = content.get("key_messages") or []
    call_to_action = content.get("call_to_action") or ""
    rationale = first.get("rationale") or ""
    summary = recommendation_record.get("analysis_summary") or ""

    description_parts = [part for part in [summary, rationale, call_to_action] if part]
    keywords = []
    for keyword in key_messages:
        text = str(keyword).strip().lower()
        if text and text not in keywords:
            keywords.append(text)

    campaign_title = str(first.get("title") or "Nouvelle campagne recommandee").strip()
    return {
        "campaign_name": campaign_title,
        "campaign_type": str(first.get("category") or "promotion").strip() or "promotion",
        "platform": str(first.get("target_platform") or "multi_platform").strip() or "multi_platform",
        "description": "\n\n".join(description_parts),
        "influencer_handle": None,
        "influencer_tier": str(influencer_profile.get("tier") or "none").strip() or "none",
        "target_segment": str(first.get("target_segment") or "").strip() or None,
        "target_aspects": list(first.get("target_aspects") or []),
        "target_regions": [str(region).lower() for region in (first.get("target_regions") or [])],
        "keywords": keywords,
        "start_date": today_value.isoformat(),
        "end_date": (today_value + timedelta(days=14)).isoformat(),
        "pre_window_days": 14,
        "post_window_days": 14,
        "timing_urgency": str(timing.get("urgency") or "").strip() or None,
    }


def _coerce_date(value: object, fallback: date) -> date:
    """Convertit une valeur libre en date Python exploitable par Streamlit."""
    if isinstance(value, date):
        return value
    if value in (None, ""):
        return fallback
    try:
        converted = pd.to_datetime(value, errors="coerce")
    except Exception:
        return fallback
    if converted is None or pd.isna(converted):
        return fallback
    return converted.date()


def _coerce_int(value: object, fallback: int) -> int:
    """Convertit une valeur numerique libre en entier stable."""
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return fallback
    if math.isnan(numeric):
        return fallback
    return int(numeric)


def _join_csv(values: object) -> str:
    """Assemble une liste de valeurs en texte CSV simple pour les champs de formulaire."""
    if not isinstance(values, list):
        return ""
    return ", ".join(str(item).strip() for item in values if str(item).strip())


def build_campaign_form_defaults(prefill: dict | None, *, today: date | None = None) -> dict:
    """Convertit un prefill metier en valeurs pretes pour le formulaire Streamlit."""
    base_date = today or date.today()
    payload = dict(prefill or {})

    return {
        "campaign_name": str(payload.get("campaign_name") or ""),
        "campaign_type": str(payload.get("campaign_type") or "promotion"),
        "platform": str(payload.get("platform") or "multi_platform"),
        "description": str(payload.get("description") or ""),
        "influencer_handle": str(payload.get("influencer_handle") or ""),
        "influencer_tier": str(payload.get("influencer_tier") or "none"),
        "target_segment": str(payload.get("target_segment") or ""),
        "target_aspects_text": _join_csv(payload.get("target_aspects")),
        "target_regions_text": _join_csv(payload.get("target_regions")),
        "keywords_text": _join_csv(payload.get("keywords")),
        "start_date": _coerce_date(payload.get("start_date"), base_date),
        "end_date": _coerce_date(payload.get("end_date"), base_date + timedelta(days=14)),
        "pre_window_days": _coerce_int(payload.get("pre_window_days"), 14),
        "post_window_days": _coerce_int(payload.get("post_window_days"), 14),
    }
