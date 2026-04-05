"""Tests TDD pour le runtime d'automatisation RamyPulse."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _import_or_fail(module_name: str):
    """Importe un module cible ou fait échouer explicitement le test."""
    try:
        return importlib.import_module(module_name)
    except ModuleNotFoundError as exc:  # pragma: no cover - chemin rouge TDD
        pytest.fail(f"Module absent: {exc}")


def test_run_automation_cycle_executes_enabled_steps(monkeypatch: pytest.MonkeyPatch) -> None:
    """Le runtime doit exécuter sync, normalisation, health et alertes dans un résumé structuré."""
    runtime = _import_or_fail("core.runtime.automation_runtime")

    monkeypatch.setattr(runtime, "run_due_syncs", lambda **kwargs: {"sources_scheduled": 2})
    monkeypatch.setattr(runtime, "run_normalization_job", lambda **kwargs: {"processed_count": 5})
    monkeypatch.setattr(
        runtime,
        "run_source_health_cycle",
        lambda **kwargs: {"sources_checked": 3, "alerts_created": 1},
    )
    monkeypatch.setattr(
        runtime,
        "run_alert_detection_cycle",
        lambda **kwargs: {"alerts_created": 4},
    )

    result = runtime.run_automation_cycle(client_id="ramy_client_001")

    assert result["client_id"] == "ramy_client_001"
    assert result["sync"]["sources_scheduled"] == 2
    assert result["normalization"]["processed_count"] == 5
    assert result["health"]["alerts_created"] == 1
    assert result["alerts"]["alerts_created"] == 4


def test_run_automation_cycle_can_skip_selected_steps(monkeypatch: pytest.MonkeyPatch) -> None:
    """Le runtime doit permettre de désactiver explicitement certaines étapes."""
    runtime = _import_or_fail("core.runtime.automation_runtime")

    sync_calls: list[str] = []
    monkeypatch.setattr(runtime, "run_due_syncs", lambda **kwargs: sync_calls.append("sync") or {})
    monkeypatch.setattr(
        runtime,
        "run_source_health_cycle",
        lambda **kwargs: {"sources_checked": 0, "alerts_created": 0},
    )
    monkeypatch.setattr(
        runtime,
        "run_alert_detection_cycle",
        lambda **kwargs: {"alerts_created": 0},
    )

    result = runtime.run_automation_cycle(
        client_id="ramy_client_001",
        run_normalization=False,
    )

    assert sync_calls == ["sync"]
    assert result["normalization"]["status"] == "skipped"
    assert result["health"]["sources_checked"] == 0
    assert result["alerts"]["alerts_created"] == 0
