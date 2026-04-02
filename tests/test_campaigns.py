"""Tests TDD pour core/campaigns — campaign_manager et impact_calculator.

Utilise une base SQLite temporaire par test via monkeypatch.
"""

from __future__ import annotations

import os
import sqlite3
import sys
from datetime import datetime, timedelta

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import config
import core.alerts.alert_manager as alert_module
import core.campaigns.campaign_manager as cm
import core.campaigns.impact_calculator as ic_module
from core.campaigns.campaign_manager import (
    create_campaign,
    delete_campaign,
    get_campaign,
    list_campaigns,
    update_campaign_status,
)
from core.campaigns.impact_calculator import (
    compute_attribution_score,
    compute_campaign_impact,
    filter_signals_for_campaign,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def use_test_db(tmp_path, monkeypatch):
    """Redirige SQLITE_DB_PATH vers une base SQLite temporaire pour chaque test."""
    db = tmp_path / "test_campaigns.db"
    monkeypatch.setattr(cm, "SQLITE_DB_PATH", db)
    monkeypatch.setattr(config, "SQLITE_DB_PATH", db)
    monkeypatch.setattr(alert_module.config, "SQLITE_DB_PATH", db)
    if hasattr(ic_module, "config"):
        monkeypatch.setattr(ic_module.config, "SQLITE_DB_PATH", db)
    return db


@pytest.fixture
def sample_campaign():
    return {
        "campaign_name": "Test Influenceur Oran",
        "campaign_type": "influencer",
        "platform": "instagram",
        "description": "Campagne test",
        "influencer_handle": "@testhandle",
        "influencer_tier": "micro",
        "target_aspects": ["emballage", "goût"],
        "target_regions": ["oran", "alger"],
        "keywords": ["ramy", "jus", "bouteille"],
        "budget_dza": 500000,
        "start_date": "2026-02-01",
        "end_date": "2026-02-15",
    }


def _make_df(n: int = 30, channel: str = "instagram", aspect: str = "emballage",
             wilaya: str = "oran", base_date: datetime | None = None) -> pd.DataFrame:
    """Crée un DataFrame synthétique avec des signaux autour d'une date centrale."""
    if base_date is None:
        base_date = datetime(2026, 2, 8)  # milieu de la campagne 1–15 fév
    rows = []
    for i in range(n):
        date = base_date + timedelta(days=i - n // 2)
        rows.append({
            "text": f"ramy jus excellent bouteille signal {i}",
            "text_original": f"ramy jus excellent bouteille signal {i}",
            "sentiment_label": "positif" if i % 3 != 0 else "négatif",
            "confidence": 0.9,
            "channel": channel,
            "aspect": aspect,
            "wilaya": wilaya,
            "timestamp": date.isoformat(),
            "source_url": "",
        })
    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    return df


# ---------------------------------------------------------------------------
# Tests campaign_manager — CRUD
# ---------------------------------------------------------------------------


def test_create_campaign_retourne_uuid(sample_campaign):
    """create_campaign() doit retourner un UUID string non vide."""
    cid = create_campaign(sample_campaign)
    assert isinstance(cid, str)
    assert len(cid) == 36  # UUID standard


def test_get_campaign_retourne_enregistrement(sample_campaign):
    """get_campaign() doit retourner le dict complet avec listes desérialisées."""
    cid = create_campaign(sample_campaign)
    camp = get_campaign(cid)
    assert camp is not None
    assert camp["campaign_name"] == "Test Influenceur Oran"
    assert camp["campaign_type"] == "influencer"
    assert camp["platform"] == "instagram"
    assert isinstance(camp["target_aspects"], list)
    assert "emballage" in camp["target_aspects"]
    assert isinstance(camp["target_regions"], list)
    assert "oran" in camp["target_regions"]
    assert isinstance(camp["keywords"], list)
    assert "ramy" in camp["keywords"]


def test_get_campaign_inexistant_retourne_none():
    """get_campaign() doit retourner None pour un ID inexistant."""
    assert get_campaign("00000000-0000-0000-0000-000000000000") is None


def test_list_campaigns_retourne_tous(sample_campaign):
    """list_campaigns() sans filtre doit retourner toutes les campagnes."""
    create_campaign(sample_campaign)
    c2 = dict(sample_campaign)
    c2["campaign_name"] = "Campagne Alger"
    create_campaign(c2)
    results = list_campaigns()
    assert len(results) == 2


def test_list_campaigns_filtre_status(sample_campaign):
    """list_campaigns(status='active') ne retourne que les campagnes actives."""
    cid = create_campaign(sample_campaign)
    update_campaign_status(cid, "active")
    c2 = dict(sample_campaign)
    c2["campaign_name"] = "Campagne planifiée"
    create_campaign(c2)
    actives = list_campaigns(status="active")
    assert len(actives) == 1
    assert actives[0]["campaign_id"] == cid


def test_list_campaigns_filtre_platform(sample_campaign):
    """list_campaigns(platform='facebook') ne retourne que les campagnes facebook."""
    create_campaign(sample_campaign)  # instagram
    c2 = dict(sample_campaign)
    c2["campaign_name"] = "Campagne Facebook"
    c2["platform"] = "facebook"
    create_campaign(c2)
    fb = list_campaigns(platform="facebook")
    assert len(fb) == 1
    assert fb[0]["campaign_name"] == "Campagne Facebook"


def test_list_campaigns_listes_deserialisees(sample_campaign):
    """list_campaigns() doit retourner les champs JSON en listes Python."""
    create_campaign(sample_campaign)
    camps = list_campaigns()
    assert isinstance(camps[0]["target_aspects"], list)
    assert isinstance(camps[0]["target_regions"], list)
    assert isinstance(camps[0]["keywords"], list)


def test_update_campaign_status_valide(sample_campaign):
    """update_campaign_status() doit retourner True et modifier le statut."""
    cid = create_campaign(sample_campaign)
    result = update_campaign_status(cid, "active")
    assert result is True
    assert get_campaign(cid)["status"] == "active"


def test_update_campaign_status_invalide(sample_campaign):
    """update_campaign_status() doit retourner False pour un statut inconnu."""
    cid = create_campaign(sample_campaign)
    result = update_campaign_status(cid, "statut_inexistant")
    assert result is False


def test_update_campaign_status_inexistant():
    """update_campaign_status() doit retourner False si la campagne n'existe pas."""
    result = update_campaign_status("00000000-0000-0000-0000-000000000000", "active")
    assert result is False


def test_delete_campaign_supprime(sample_campaign):
    """delete_campaign() doit supprimer la campagne et retourner True."""
    cid = create_campaign(sample_campaign)
    assert delete_campaign(cid) is True
    assert get_campaign(cid) is None


def test_delete_campaign_inexistant():
    """delete_campaign() doit retourner False si la campagne n'existe pas."""
    assert delete_campaign("00000000-0000-0000-0000-000000000000") is False


def test_campaign_client_id_defaut(sample_campaign):
    """create_campaign() doit utiliser DEFAULT_CLIENT_ID si client_id absent."""
    cid = create_campaign(sample_campaign)
    camp = get_campaign(cid)
    assert camp["client_id"] == "ramy_client_001"


def test_campaign_champs_optionnels_none():
    """create_campaign() doit fonctionner avec seulement campaign_name."""
    cid = create_campaign({"campaign_name": "Minimal"})
    camp = get_campaign(cid)
    assert camp is not None
    assert camp["campaign_name"] == "Minimal"
    assert camp["target_aspects"] == []
    assert camp["keywords"] == []
    assert camp["status"] == "planned"


# ---------------------------------------------------------------------------
# Tests filter_signals_for_campaign
# ---------------------------------------------------------------------------


def test_filter_signals_filtre_temporel():
    """filter_signals_for_campaign() doit exclure les signaux hors fenêtre."""
    df = _make_df(n=60, base_date=datetime(2026, 2, 8))
    campaign = {"platform": None, "target_aspects": [], "target_regions": [], "keywords": []}
    filtered = filter_signals_for_campaign(df, campaign, "2026-02-01", "2026-02-15")
    ts = filtered["timestamp"]
    assert (ts >= pd.Timestamp("2026-02-01")).all()
    assert (ts <= pd.Timestamp("2026-02-15")).all()


def test_filter_signals_filtre_channel():
    """filter_signals_for_campaign() doit filtrer par platform si != multi_platform."""
    df = _make_df(n=20)
    df_fb = _make_df(n=10, channel="facebook")
    df_all = pd.concat([df, df_fb], ignore_index=True)
    campaign = {"platform": "instagram", "target_aspects": [], "target_regions": [], "keywords": []}
    filtered = filter_signals_for_campaign(df_all, campaign, "2026-01-01", "2026-12-31")
    assert (filtered["channel"] == "instagram").all()


def test_filter_signals_multi_platform_ne_filtre_pas_channel():
    """filter_signals_for_campaign() ne filtre pas le channel si multi_platform."""
    df = _make_df(n=10)
    df_fb = _make_df(n=10, channel="facebook")
    df_all = pd.concat([df, df_fb], ignore_index=True)
    campaign = {"platform": "multi_platform", "target_aspects": [], "target_regions": [], "keywords": []}
    filtered = filter_signals_for_campaign(df_all, campaign, "2026-01-01", "2026-12-31")
    assert len(filtered) == 20


def test_filter_signals_filtre_aspect():
    """filter_signals_for_campaign() filtre par target_aspects si non vide."""
    df_emb = _make_df(n=10, aspect="emballage")
    df_gout = _make_df(n=10, aspect="goût")
    df_all = pd.concat([df_emb, df_gout], ignore_index=True)
    campaign = {"platform": None, "target_aspects": ["emballage"], "target_regions": [], "keywords": []}
    filtered = filter_signals_for_campaign(df_all, campaign, "2026-01-01", "2026-12-31")
    assert (filtered["aspect"] == "emballage").all()
    assert len(filtered) == 10


def test_filter_signals_filtre_wilaya():
    """filter_signals_for_campaign() filtre par target_regions si non vide."""
    df_oran = _make_df(n=10, wilaya="oran")
    df_alger = _make_df(n=10, wilaya="alger")
    df_all = pd.concat([df_oran, df_alger], ignore_index=True)
    campaign = {"platform": None, "target_aspects": [], "target_regions": ["oran"], "keywords": []}
    filtered = filter_signals_for_campaign(df_all, campaign, "2026-01-01", "2026-12-31")
    assert (filtered["wilaya"] == "oran").all()


def test_filter_signals_filtre_keywords():
    """filter_signals_for_campaign() filtre par keyword dans le texte."""
    rows_match = [{"text": "ramy jus super", "timestamp": datetime(2026, 2, 5).isoformat(),
                   "channel": "instagram", "aspect": "goût", "wilaya": "oran",
                   "sentiment_label": "positif", "confidence": 0.9, "source_url": ""}]
    rows_no_match = [{"text": "autre marque bien", "timestamp": datetime(2026, 2, 5).isoformat(),
                      "channel": "instagram", "aspect": "goût", "wilaya": "oran",
                      "sentiment_label": "positif", "confidence": 0.9, "source_url": ""}]
    df = pd.DataFrame(rows_match + rows_no_match)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    campaign = {"platform": None, "target_aspects": [], "target_regions": [], "keywords": ["ramy"]}
    filtered = filter_signals_for_campaign(df, campaign, "2026-01-01", "2026-12-31")
    assert len(filtered) == 1
    assert "ramy" in filtered.iloc[0]["text"]


def test_filter_signals_df_vide():
    """filter_signals_for_campaign() sur DataFrame vide retourne DataFrame vide."""
    campaign = {"platform": "instagram", "target_aspects": ["emballage"],
                "target_regions": ["oran"], "keywords": ["ramy"]}
    result = filter_signals_for_campaign(pd.DataFrame(), campaign, "2026-01-01", "2026-12-31")
    assert result.empty


def test_filter_signals_inclut_toute_la_journee_de_fin():
    """La date de fin au format YYYY-MM-DD doit inclure les signaux de toute la journee."""
    df = pd.DataFrame(
        [
            {
                "text": "ramy signal fin de campagne",
                "text_original": "ramy signal fin de campagne",
                "sentiment_label": "positif",
                "confidence": 0.9,
                "channel": "instagram",
                "aspect": "goût",
                "wilaya": "oran",
                "timestamp": "2026-02-15T12:30:00",
                "source_url": "",
            }
        ]
    )
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    campaign = {"platform": "instagram", "target_aspects": [], "target_regions": [], "keywords": ["ramy"]}

    filtered = filter_signals_for_campaign(df, campaign, "2026-02-01", "2026-02-15")

    assert len(filtered) == 1


# ---------------------------------------------------------------------------
# Tests compute_attribution_score
# ---------------------------------------------------------------------------


def test_attribution_score_base():
    """Score de base (hors handle/keywords/aspect) doit être 0.3."""
    row = pd.Series({"text": "bon produit", "aspect": "prix"})
    campaign = {"influencer_handle": None, "keywords": [], "target_aspects": []}
    score = compute_attribution_score(row, campaign)
    assert score == pytest.approx(0.3)


def test_attribution_score_avec_handle():
    """Handle influenceur dans le texte ajoute 0.4."""
    row = pd.Series({"text": "j'adore le post de @testhandle sur ramy", "aspect": "goût"})
    campaign = {"influencer_handle": "@testhandle", "keywords": [], "target_aspects": []}
    score = compute_attribution_score(row, campaign)
    assert score == pytest.approx(0.7)


def test_attribution_score_avec_keyword():
    """Keyword présent dans le texte ajoute 0.2."""
    row = pd.Series({"text": "j'ai acheté ramy hier", "aspect": "prix"})
    campaign = {"influencer_handle": None, "keywords": ["ramy"], "target_aspects": []}
    score = compute_attribution_score(row, campaign)
    assert score == pytest.approx(0.5)


def test_attribution_score_avec_aspect():
    """Aspect correspondant ajoute 0.1."""
    row = pd.Series({"text": "bon produit", "aspect": "emballage"})
    campaign = {"influencer_handle": None, "keywords": [], "target_aspects": ["emballage"]}
    score = compute_attribution_score(row, campaign)
    assert score == pytest.approx(0.4)


def test_attribution_score_max_1():
    """Le score ne dépasse jamais 1.0."""
    row = pd.Series({"text": "@testhandle ramy emballage", "aspect": "emballage"})
    campaign = {"influencer_handle": "@testhandle", "keywords": ["ramy"], "target_aspects": ["emballage"]}
    score = compute_attribution_score(row, campaign)
    assert score <= 1.0


# ---------------------------------------------------------------------------
# Tests compute_campaign_impact
# ---------------------------------------------------------------------------


def test_compute_campaign_impact_structure(sample_campaign):
    """compute_campaign_impact() doit retourner un dict avec les clés obligatoires."""
    cid = create_campaign(sample_campaign)
    df = _make_df(n=90, base_date=datetime(2026, 2, 8))
    result = compute_campaign_impact(cid, df)
    assert "campaign_id" in result
    assert "campaign_name" in result
    assert "phases" in result
    assert "pre" in result["phases"]
    assert "active" in result["phases"]
    assert "post" in result["phases"]
    assert "uplift_nss" in result
    assert "uplift_volume_pct" in result
    assert "is_reliable" in result
    assert "reliability_note" in result


def test_compute_campaign_impact_phase_keys(sample_campaign):
    """Chaque phase doit contenir nss, volume, aspect_breakdown, sentiment_breakdown."""
    cid = create_campaign(sample_campaign)
    df = _make_df(n=30, base_date=datetime(2026, 2, 8))
    result = compute_campaign_impact(cid, df)
    for phase_name in ("pre", "active", "post"):
        phase = result["phases"][phase_name]
        assert "nss" in phase
        assert "volume" in phase
        assert isinstance(phase["volume"], int)
        assert "aspect_breakdown" in phase
        assert "sentiment_breakdown" in phase


def test_compute_campaign_impact_volume_non_negatif(sample_campaign):
    """Le volume de chaque phase doit être >= 0."""
    cid = create_campaign(sample_campaign)
    df = _make_df(n=30, base_date=datetime(2026, 2, 8))
    result = compute_campaign_impact(cid, df)
    for phase in result["phases"].values():
        assert phase["volume"] >= 0


def test_compute_campaign_impact_id_inexistant():
    """compute_campaign_impact() sur un ID inexistant doit retourner is_reliable=False."""
    df = _make_df(n=30)
    result = compute_campaign_impact("00000000-0000-0000-0000-000000000000", df)
    assert result["is_reliable"] is False
    assert result["campaign_name"] is None


def test_compute_campaign_impact_df_vide(sample_campaign):
    """compute_campaign_impact() sur DataFrame vide retourne volumes à 0."""
    cid = create_campaign(sample_campaign)
    result = compute_campaign_impact(cid, pd.DataFrame())
    for phase in result["phases"].values():
        assert phase["volume"] == 0


def test_compute_campaign_impact_is_reliable_faux_si_volume_insuffisant(sample_campaign):
    """is_reliable=False si volume < MIN_SIGNALS_FOR_ATTRIBUTION dans une phase."""
    cid = create_campaign(sample_campaign)
    # Seulement 5 signaux — insuffisant
    df = _make_df(n=5, base_date=datetime(2026, 2, 8))
    result = compute_campaign_impact(cid, df)
    assert result["is_reliable"] is False
    assert result["reliability_note"] != ""


def test_compute_campaign_impact_respecte_les_bornes_pre_active_post(sample_campaign):
    """Les bornes PRD doivent garder le jour de debut en active et le lendemain de fin en post."""
    cid = create_campaign(sample_campaign)
    df = pd.DataFrame(
        [
            {
                "text": "pre",
                "text_original": "pre",
                "sentiment_label": "positif",
                "confidence": 0.9,
                "channel": "instagram",
                "aspect": "emballage",
                "wilaya": "oran",
                "timestamp": "2026-01-31T12:00:00",
                "source_url": "",
            },
            {
                "text": "active start",
                "text_original": "active start",
                "sentiment_label": "positif",
                "confidence": 0.9,
                "channel": "instagram",
                "aspect": "emballage",
                "wilaya": "oran",
                "timestamp": "2026-02-01T12:00:00",
                "source_url": "",
            },
            {
                "text": "active end noon",
                "text_original": "active end noon",
                "sentiment_label": "négatif",
                "confidence": 0.9,
                "channel": "instagram",
                "aspect": "emballage",
                "wilaya": "oran",
                "timestamp": "2026-02-15T12:00:00",
                "source_url": "",
            },
            {
                "text": "post",
                "text_original": "post",
                "sentiment_label": "positif",
                "confidence": 0.9,
                "channel": "instagram",
                "aspect": "emballage",
                "wilaya": "oran",
                "timestamp": "2026-02-16T12:00:00",
                "source_url": "",
            },
        ]
    )
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    result = compute_campaign_impact(cid, df)

    assert result["phases"]["pre"]["volume"] == 1
    assert result["phases"]["active"]["volume"] == 2
    assert result["phases"]["post"]["volume"] == 1


def test_compute_campaign_impact_persiste_snapshots_et_liens_signaux(sample_campaign):
    """Le calcul doit persister les snapshots de phase et les liens de signaux attribues."""
    cid = create_campaign(sample_campaign)
    df = pd.DataFrame(
        [
            {
                "text": "pre",
                "text_original": "pre",
                "sentiment_label": "positif",
                "confidence": 0.9,
                "channel": "instagram",
                "aspect": "emballage",
                "wilaya": "oran",
                "timestamp": "2026-01-31T12:00:00",
                "source_url": "https://example.test/pre",
            },
            {
                "text": "active",
                "text_original": "active",
                "sentiment_label": "positif",
                "confidence": 0.9,
                "channel": "instagram",
                "aspect": "emballage",
                "wilaya": "oran",
                "timestamp": "2026-02-10T12:00:00",
                "source_url": "https://example.test/active",
            },
            {
                "text": "post",
                "text_original": "post",
                "sentiment_label": "positif",
                "confidence": 0.9,
                "channel": "instagram",
                "aspect": "emballage",
                "wilaya": "oran",
                "timestamp": "2026-02-16T12:00:00",
                "source_url": "https://example.test/post",
            },
        ]
    )
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    compute_campaign_impact(cid, df)

    with sqlite3.connect(config.SQLITE_DB_PATH) as connection:
        snapshots = connection.execute(
            "SELECT phase FROM campaign_metrics_snapshots WHERE campaign_id = ? ORDER BY phase",
            (cid,),
        ).fetchall()
        links = connection.execute(
            "SELECT phase, signal_id FROM campaign_signal_links WHERE campaign_id = ? ORDER BY phase, signal_id",
            (cid,),
        ).fetchall()

    assert [row[0] for row in snapshots] == ["active", "post", "pre"]
    assert len(links) == 3
    assert {row[0] for row in links} == {"pre", "active", "post"}


def test_compute_campaign_impact_cree_alerte_campaign_impact_positive(sample_campaign):
    """Un uplift NSS positif suffisant doit creer une alerte campagne dediee."""
    cid = create_campaign(sample_campaign)
    df = pd.DataFrame(
        [
            {
                "text": f"pre {index}",
                "text_original": f"pre {index}",
                "sentiment_label": "négatif",
                "confidence": 0.9,
                "channel": "instagram",
                "aspect": "emballage",
                "wilaya": "oran",
                "timestamp": f"2026-01-{25 + index:02d}T12:00:00",
                "source_url": f"https://example.test/pre-{index}",
            }
            for index in range(6)
        ]
        + [
            {
                "text": f"post {index}",
                "text_original": f"post {index}",
                "sentiment_label": "positif",
                "confidence": 0.9,
                "channel": "instagram",
                "aspect": "emballage",
                "wilaya": "oran",
                "timestamp": f"2026-02-{16 + index:02d}T12:00:00",
                "source_url": f"https://example.test/post-{index}",
            }
            for index in range(6)
        ]
    )
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    compute_campaign_impact(cid, df)

    alerts = alert_module.list_alerts(limit=50)

    positive_alerts = [
        alert for alert in alerts if alert["alert_rule_id"] == "campaign_impact_positive"
    ]
    assert len(positive_alerts) == 1
    assert positive_alerts[0]["alert_payload"]["campaign_id"] == cid


def test_compute_campaign_impact_cree_alerte_campaign_underperformance() -> None:
    """Une campagne active depuis plus de 7 jours sans uplift doit creer une alerte dediee."""
    cid = create_campaign(
        {
            "campaign_name": "Campagne en sous-performance",
            "campaign_type": "promotion",
            "platform": "instagram",
            "target_aspects": ["emballage"],
            "target_regions": ["oran"],
            "keywords": ["ramy"],
            "start_date": "2026-03-01",
            "end_date": "2026-03-20",
            "status": "active",
        }
    )
    df = pd.DataFrame(
        [
            {
                "text": f"pre {index} ramy",
                "text_original": f"pre {index} ramy",
                "sentiment_label": "positif",
                "confidence": 0.9,
                "channel": "instagram",
                "aspect": "emballage",
                "wilaya": "oran",
                "timestamp": (
                    pd.Timestamp("2026-01-30T12:00:00") + pd.Timedelta(days=index)
                ).isoformat(),
                "source_url": f"https://example.test/preu-{index}",
            }
            for index in range(30)
        ]
        + [
            {
                "text": f"active {index} ramy",
                "text_original": f"active {index} ramy",
                "sentiment_label": "négatif",
                "confidence": 0.9,
                "channel": "instagram",
                "aspect": "emballage",
                "wilaya": "oran",
                "timestamp": (
                    pd.Timestamp("2026-03-10T12:00:00") + pd.Timedelta(hours=index * 4)
                ).isoformat(),
                "source_url": f"https://example.test/activeu-{index}",
            }
            for index in range(60)
        ]
    )
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    compute_campaign_impact(cid, df)

    alerts = alert_module.list_alerts(limit=50)
    underperformance_alerts = [
        alert for alert in alerts if alert["alert_rule_id"] == "campaign_underperformance"
    ]

    assert len(underperformance_alerts) == 1
    assert underperformance_alerts[0]["alert_payload"]["campaign_id"] == cid
