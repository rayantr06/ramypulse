"""Tests de structure du dossier pages pour Streamlit."""

from __future__ import annotations

from pathlib import Path


def test_pages_directory_ne_contient_pas_de_helpers_exposes() -> None:
    """Les helpers Python ne doivent pas apparaitre comme fausses pages Streamlit."""
    pages_dir = Path(__file__).resolve().parents[1] / "pages"
    helper_files = {
        "campaigns_helpers.py",
        "phase1_admin_helpers.py",
        "phase1_dashboard_helpers.py",
        "whatif_helpers.py",
    }

    existing_helpers = {path.name for path in pages_dir.glob("*.py")} & helper_files

    assert existing_helpers == set()
