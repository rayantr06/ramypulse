"""Tests TDD pour les watchlists RamyPulse."""

from __future__ import annotations

import importlib
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config  # noqa: E402


def _import_or_fail(module_name: str):
    """Importe un module cible ou fait echouer explicitement le test."""
    try:
        return importlib.import_module(module_name)
    except ModuleNotFoundError as exc:  # pragma: no cover - chemin rouge TDD
        pytest.fail(f"Module absent: {exc}")


def _prepare_sqlite(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Configure un fichier SQLite temporaire pour les tests de watchlists."""
    db_path = tmp_path / "watchlists.db"
    monkeypatch.setattr(config, "SQLITE_DB_PATH", db_path)
    return db_path


def _raw_filters(**overrides: object) -> dict[str, object]:
    """Construit un filtre de watchlist conforme au contrat."""
    filters: dict[str, object] = {
        "channel": "google_maps",
        "aspect": "disponibilité",
        "wilaya": "oran",
        "product": "ramy_citron",
        "sentiment": None,
        "period_days": 7,
        "min_volume": 10,
    }
    filters.update(overrides)
    return filters


def test_watchlist_manager_expose_le_contrat_public() -> None:
    """Le module doit exposer les 5 fonctions du contrat INTERFACES."""
    module = _import_or_fail("core.watchlists.watchlist_manager")

    for function_name in (
        "create_watchlist",
        "list_watchlists",
        "get_watchlist",
        "update_watchlist",
        "deactivate_watchlist",
    ):
        assert hasattr(module, function_name), f"Fonction manquante: {function_name}"


def test_create_watchlist_persiste_et_deserialise_les_filtres(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """La creation doit persister un JSON et le relire en dict."""
    _prepare_sqlite(monkeypatch, tmp_path)
    manager = _import_or_fail("core.watchlists.watchlist_manager")

    watchlist_id = manager.create_watchlist(
        name="NSS Livraison Oran",
        description="Surveille la disponibilite sur Oran",
        scope_type="region",
        filters=_raw_filters(),
    )

    watchlist = manager.get_watchlist(watchlist_id)

    assert watchlist is not None
    assert watchlist["watchlist_id"] == watchlist_id
    assert watchlist["watchlist_name"] == "NSS Livraison Oran"
    assert watchlist["scope_type"] == "region"
    assert watchlist["is_active"] == 1
    assert watchlist["filters"]["channel"] == "google_maps"
    assert watchlist["filters"]["period_days"] == 7
    assert watchlist["client_id"] == config.DEFAULT_CLIENT_ID
    assert watchlist["created_at"]
    assert watchlist["updated_at"]

    with sqlite3.connect(config.SQLITE_DB_PATH) as connection:
        row = connection.execute(
            "SELECT filters FROM watchlists WHERE watchlist_id = ?",
            (watchlist_id,),
        ).fetchone()
    assert isinstance(row[0], str)
    assert '"channel": "google_maps"' in row[0]


def test_list_watchlists_exclut_les_inactives_par_defaut(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Le listing par defaut doit ne retourner que les watchlists actives."""
    _prepare_sqlite(monkeypatch, tmp_path)
    manager = _import_or_fail("core.watchlists.watchlist_manager")

    active_id = manager.create_watchlist(
        name="Active",
        description="active",
        scope_type="product",
        filters=_raw_filters(product="ramy_orange"),
    )
    inactive_id = manager.create_watchlist(
        name="Inactive",
        description="inactive",
        scope_type="region",
        filters=_raw_filters(wilaya="tlemcen"),
    )
    assert manager.deactivate_watchlist(inactive_id) is True

    active_only = manager.list_watchlists()
    all_rows = manager.list_watchlists(is_active=False)

    assert [row["watchlist_id"] for row in active_only] == [active_id]
    assert {row["watchlist_id"] for row in all_rows} == {active_id, inactive_id}


def test_update_watchlist_supporte_une_mise_a_jour_partielle(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """La mise a jour partielle doit persister nom, description et filtres."""
    _prepare_sqlite(monkeypatch, tmp_path)
    manager = _import_or_fail("core.watchlists.watchlist_manager")

    watchlist_id = manager.create_watchlist(
        name="A mettre a jour",
        description="avant",
        scope_type="channel",
        filters=_raw_filters(channel="facebook"),
    )

    updated = manager.update_watchlist(
        watchlist_id,
        {
            "watchlist_name": "Apres mise a jour",
            "description": "apres",
            "filters": _raw_filters(channel="youtube", min_volume=25),
        },
    )

    assert updated is True
    watchlist = manager.get_watchlist(watchlist_id)
    assert watchlist is not None
    assert watchlist["watchlist_name"] == "Apres mise a jour"
    assert watchlist["description"] == "apres"
    assert watchlist["filters"]["channel"] == "youtube"
    assert watchlist["filters"]["min_volume"] == 25


def test_deactivate_watchlist_met_is_active_a_zero(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """La desactivation doit conserver la ligne mais la rendre inactive."""
    _prepare_sqlite(monkeypatch, tmp_path)
    manager = _import_or_fail("core.watchlists.watchlist_manager")

    watchlist_id = manager.create_watchlist(
        name="Temporaire",
        description="temp",
        scope_type="cross_dimension",
        filters=_raw_filters(channel=None, aspect=None),
    )

    result = manager.deactivate_watchlist(watchlist_id)
    watchlist = manager.get_watchlist(watchlist_id)

    assert result is True
    assert watchlist is not None
    assert watchlist["is_active"] == 0
