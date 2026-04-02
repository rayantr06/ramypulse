"""Tests TDD pour le pre-remplissage campagne depuis une recommandation."""

from __future__ import annotations

from datetime import date
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_build_campaign_prefill_from_recommendation_record() -> None:
    """Une recommendation doit produire un prefill exploitable pour le formulaire campagne."""
    from core.campaigns.campaign_prefill import build_campaign_prefill_from_recommendation_record

    recommendation_record = {
        "analysis_summary": "NSS disponibilite en baisse sur Oran.",
        "recommendations": [
            {
                "title": "Influenceur micro Instagram Oran",
                "category": "promotion",
                "priority": "high",
                "rationale": "Concentrer la relance sur Oran",
                "target_platform": "instagram",
                "target_segment": "gen_z_18_25",
                "target_regions": ["oran"],
                "target_aspects": ["disponibilite"],
                "timing": {"urgency": "within_week"},
                "influencer_profile": {"tier": "micro"},
                "content": {
                    "key_messages": ["ramy", "disponible maintenant"],
                    "call_to_action": "Dis-nous ton quartier",
                },
            }
        ],
    }

    prefill = build_campaign_prefill_from_recommendation_record(recommendation_record)

    assert prefill["campaign_type"] == "promotion"
    assert prefill["platform"] == "instagram"
    assert prefill["target_segment"] == "gen_z_18_25"
    assert prefill["target_regions"] == ["oran"]
    assert prefill["target_aspects"] == ["disponibilite"]
    assert "Dis-nous ton quartier" in prefill["description"]
    assert "ramy" in prefill["keywords"]


def test_build_campaign_form_defaults_convertit_les_prefills_pour_streamlit() -> None:
    """Les valeurs de pre-remplissage doivent etre converties en types/formats exploitables par la page."""
    from core.campaigns.campaign_prefill import build_campaign_form_defaults

    defaults = build_campaign_form_defaults(
        {
            "campaign_name": "Campagne recommandee",
            "campaign_type": "promotion",
            "platform": "instagram",
            "description": "Message",
            "influencer_handle": "@ramy",
            "influencer_tier": "micro",
            "target_segment": "gen_z_18_25",
            "target_aspects": ["disponibilite", "prix"],
            "target_regions": ["oran", "alger"],
            "keywords": ["ramy", "promo"],
            "start_date": "2026-04-06",
            "end_date": "2026-04-20",
            "pre_window_days": 10,
            "post_window_days": 20,
        }
    )

    assert defaults["campaign_name"] == "Campagne recommandee"
    assert defaults["target_segment"] == "gen_z_18_25"
    assert defaults["target_aspects_text"] == "disponibilite, prix"
    assert defaults["target_regions_text"] == "oran, alger"
    assert defaults["keywords_text"] == "ramy, promo"
    assert defaults["start_date"] == date(2026, 4, 6)
    assert defaults["end_date"] == date(2026, 4, 20)
