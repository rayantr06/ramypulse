"""Tests TDD pour la gestion locale et référencée des secrets."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config  # noqa: E402


def _config_module():
    """Retourne le module config courant, meme apres reload."""
    return importlib.import_module("config")


@pytest.fixture
def temp_secret_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirige le store local de secrets vers un fichier temporaire."""
    secret_store = tmp_path / "secrets.json"
    monkeypatch.setattr(_config_module(), "SECRETS_STORE_PATH", secret_store, raising=False)
    return secret_store


def test_store_secret_retourne_reference_locale(temp_secret_store: Path) -> None:
    """Un secret brut doit etre stocke hors base et retourner une reference locale."""
    from core.security.secret_manager import resolve_secret, store_secret

    reference = store_secret("sk-live-123", label="openai")

    assert reference.startswith("local:")
    assert temp_secret_store.exists()
    assert resolve_secret(reference) == "sk-live-123"


def test_resolve_secret_depuis_variable_environnement(
    temp_secret_store: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Une reference env:VAR doit etre resolue depuis les variables d'environnement."""
    from core.security.secret_manager import resolve_secret

    monkeypatch.setenv("RAMYPULSE_TEST_SECRET", "super-secret")

    assert resolve_secret("env:RAMYPULSE_TEST_SECRET") == "super-secret"


def test_store_secret_reutilise_reference_si_valeur_identique(temp_secret_store: Path) -> None:
    """Le meme secret ne doit pas dupliquer inutilement le store local."""
    from core.security.secret_manager import store_secret

    first = store_secret("same-value", label="anthropic")
    second = store_secret("same-value", label="anthropic")

    assert first == second


def test_resolve_secret_retourne_none_si_reference_inconnue(temp_secret_store: Path) -> None:
    """Une reference inconnue doit retourner None proprement."""
    from core.security.secret_manager import resolve_secret

    assert resolve_secret("local:missing-secret-id") is None
