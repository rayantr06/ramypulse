"""Tests des helpers d'administration des sources."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ui_helpers.phase1_admin_helpers import (  # noqa: E402
    build_sources_frame,
    compute_source_metrics,
    filter_source_records,
)


def _sample_sources() -> list[dict]:
    """Construit quelques sources pour les tests."""
    return [
        {
            "source_id": "src-1",
            "display_name": "Ramy Facebook",
            "platform": "facebook",
            "owner_type": "owned",
            "source_type": "facebook_page",
            "brand": "Ramy",
            "is_active": 1,
            "last_sync_at": "2026-03-20T10:00:00Z",
        },
        {
            "source_id": "src-2",
            "display_name": "Ifri Instagram",
            "platform": "instagram",
            "owner_type": "competitor",
            "source_type": "instagram_profile",
            "brand": "Ifri",
            "is_active": 0,
            "last_sync_at": None,
        },
    ]


def test_filter_source_records_applique_statut_et_plateforme() -> None:
    """Les filtres admin sources doivent restreindre les enregistrements affichés."""
    records = _sample_sources()

    filtered = filter_source_records(
        records,
        platform="facebook",
        owner_type="owned",
        status="active",
    )

    assert len(filtered) == 1
    assert filtered[0]["source_id"] == "src-1"


def test_compute_source_metrics_compte_actives_et_inactives() -> None:
    """Le résumé admin doit exposer des compteurs métier simples."""
    metrics = compute_source_metrics(_sample_sources())

    assert metrics["total"] == 2
    assert metrics["active"] == 1
    assert metrics["inactive"] == 1
    assert metrics["platforms"] == 2


def test_build_sources_frame_garde_ordre_colonnes_attendu() -> None:
    """Le tableau admin sources doit rester lisible même en base vide."""
    frame = build_sources_frame(_sample_sources())
    empty_frame = build_sources_frame([])

    assert list(frame.columns)[:4] == [
        "source_id",
        "display_name",
        "platform",
        "owner_type",
    ]
    assert list(empty_frame.columns) == list(frame.columns)
