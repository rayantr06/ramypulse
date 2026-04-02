"""Tests TDD pour le point d'entree manuel du rapport hebdomadaire."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_main_declenche_le_job_hebdo_quand_le_parquet_est_present(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Le script doit charger annotated.parquet et appeler le job avec la date fournie."""
    import config
    import scripts.run_weekly_recommendation_report as weekly_script

    annotated_path = tmp_path / "annotated.parquet"
    pd.DataFrame(
        [
            {
                "text": "ramy",
                "text_original": "ramy",
                "sentiment_label": "positif",
                "channel": "instagram",
                "aspect": "disponibilite",
                "timestamp": "2026-04-06T10:00:00",
            }
        ]
    ).to_parquet(annotated_path)

    captured: dict = {}

    def _fake_job(df_annotated, current_date=None, client_id=None):
        captured["shape"] = df_annotated.shape
        captured["current_date"] = current_date
        captured["client_id"] = client_id
        return {"recommendation_id": "rec-1"}

    monkeypatch.setattr(config, "ANNOTATED_PARQUET_PATH", annotated_path)
    monkeypatch.setattr(weekly_script, "run_weekly_recommendation_job", _fake_job)

    exit_code = weekly_script.main(["--date", "2026-04-06"])

    assert exit_code == 0
    assert captured["shape"] == (1, 6)
    assert str(captured["current_date"].date()) == "2026-04-06"


def test_main_retourne_1_si_annotated_parquet_est_absent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Le script doit echouer proprement si le fichier source est absent."""
    import config
    import scripts.run_weekly_recommendation_report as weekly_script

    monkeypatch.setattr(config, "ANNOTATED_PARQUET_PATH", tmp_path / "absent.parquet")

    exit_code = weekly_script.main([])

    assert exit_code == 1
