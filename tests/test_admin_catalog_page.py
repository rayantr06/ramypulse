"""Tests des helpers d'administration du catalogue métier."""

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pages.phase1_admin_helpers import (  # noqa: E402
    build_catalog_frame,
    compute_catalog_metrics,
    parse_keywords,
)


def test_parse_keywords_nettoie_les_entrees_vides() -> None:
    """Les mots-clés saisis doivent être découpés proprement."""
    assert parse_keywords(" jus orange,  orange  , ,ramy ") == [
        "jus orange",
        "orange",
        "ramy",
    ]


def test_build_catalog_frame_preserve_colonnes_souhaitees() -> None:
    """Le tableau admin catalogue doit garder les colonnes prioritaires."""
    frame = build_catalog_frame(
        [
            {
                "product_id": 1,
                "brand": "Ramy",
                "product_name": "Jus orange",
                "category": "jus",
                "is_active": 1,
            }
        ],
        ["product_id", "brand", "product_name", "category", "is_active"],
    )

    assert isinstance(frame, pd.DataFrame)
    assert list(frame.columns) == [
        "product_id",
        "brand",
        "product_name",
        "category",
        "is_active",
    ]


def test_compute_catalog_metrics_assemble_resume() -> None:
    """Le résumé catalogue doit exposer les compteurs des trois vues."""
    metrics = compute_catalog_metrics(
        products=[{"product_id": 1}, {"product_id": 2}],
        wilayas=[{"wilaya_code": "06"}],
        competitors=[{"competitor_id": 1}, {"competitor_id": 2}, {"competitor_id": 3}],
    )

    assert metrics == {
        "products": 2,
        "wilayas": 1,
        "competitors": 3,
    }
