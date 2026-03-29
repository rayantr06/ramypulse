"""Tests TDD pour le Source Registry SQLite."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import DatabaseManager  # noqa: E402
from core.source_registry import SourceRegistry  # noqa: E402


def _make_registry() -> tuple[DatabaseManager, SourceRegistry]:
    """Construit un registre basé sur une base SQLite en mémoire."""
    db = DatabaseManager(":memory:")
    db.create_tables()
    return db, SourceRegistry(db)


def _payload(**overrides) -> dict:
    """Retourne une source valide minimale pour les tests."""
    data = {
        "source_id": "src-001",
        "platform": "facebook",
        "source_type": "facebook_page",
        "display_name": "Page Facebook Ramy",
        "external_id": "fb-123",
        "url": "https://facebook.com/ramy",
        "owner_type": "owned",
        "auth_mode": "oauth",
        "brand": "Ramy",
        "sync_frequency": "daily",
    }
    data.update(overrides)
    return data


def test_create_source_persiste_une_ligne() -> None:
    """La création d'une source doit insérer une ligne lisible ensuite."""
    db, registry = _make_registry()

    source = registry.create_source(_payload())

    fetched = registry.get_source(source["source_id"])
    assert fetched is not None
    assert fetched["display_name"] == "Page Facebook Ramy"
    db.close()


def test_create_source_genere_source_id_si_absent() -> None:
    """Si source_id est absent, le registre doit en générer un."""
    db, registry = _make_registry()

    source = registry.create_source(_payload(source_id=None))

    assert source["source_id"]
    db.close()


def test_create_source_rejette_plateforme_invalide() -> None:
    """Une plateforme inconnue doit être rejetée proprement."""
    db, registry = _make_registry()

    with pytest.raises(ValueError, match="platform"):
        registry.create_source(_payload(platform="tiktok"))
    db.close()


def test_create_source_rejette_owner_type_invalide() -> None:
    """Un owner_type inconnu doit être rejeté proprement."""
    db, registry = _make_registry()

    with pytest.raises(ValueError, match="owner_type"):
        registry.create_source(_payload(owner_type="random"))
    db.close()


def test_list_sources_retourne_les_sources_creees() -> None:
    """Le listing doit retourner toutes les sources présentes."""
    db, registry = _make_registry()
    registry.create_source(_payload(source_id="src-001"))
    registry.create_source(_payload(source_id="src-002", platform="youtube", source_type="youtube_channel"))

    rows = registry.list_sources()

    assert len(rows) == 2
    db.close()


def test_list_sources_peut_filtrer_par_plateforme() -> None:
    """Le filtre par plateforme doit restreindre les résultats."""
    db, registry = _make_registry()
    registry.create_source(_payload(source_id="src-001", platform="facebook"))
    registry.create_source(_payload(source_id="src-002", platform="youtube", source_type="youtube_channel"))

    rows = registry.list_sources(platform="youtube")

    assert len(rows) == 1
    assert rows[0]["platform"] == "youtube"
    db.close()


def test_update_source_modifie_display_name() -> None:
    """La mise à jour doit persister les champs modifiables."""
    db, registry = _make_registry()
    registry.create_source(_payload())

    updated = registry.update_source("src-001", {"display_name": "Nouvelle page Ramy"})

    assert updated["display_name"] == "Nouvelle page Ramy"
    db.close()


def test_mark_sync_met_a_jour_last_sync_at() -> None:
    """Le marquage de synchronisation doit renseigner last_sync_at."""
    db, registry = _make_registry()
    registry.create_source(_payload())

    synced = registry.mark_sync("src-001", "2026-03-28T10:00:00Z")

    assert synced["last_sync_at"] == "2026-03-28T10:00:00Z"
    db.close()


def test_deactivate_source_met_is_active_a_zero() -> None:
    """La désactivation doit conserver la source mais la rendre inactive."""
    db, registry = _make_registry()
    registry.create_source(_payload())

    deactivated = registry.deactivate_source("src-001")

    assert deactivated["is_active"] == 0
    db.close()


def test_reactivate_source_remet_is_active_a_un() -> None:
    """La réactivation doit remettre la source en service."""
    db, registry = _make_registry()
    registry.create_source(_payload())
    registry.deactivate_source("src-001")

    reactivated = registry.reactivate_source("src-001")

    assert reactivated["is_active"] == 1
    db.close()


def test_list_sources_active_only_exclut_les_inactives() -> None:
    """Le filtre active_only doit exclure les sources désactivées."""
    db, registry = _make_registry()
    registry.create_source(_payload(source_id="src-001"))
    registry.create_source(_payload(source_id="src-002", platform="youtube", source_type="youtube_channel"))
    registry.deactivate_source("src-002")

    rows = registry.list_sources(active_only=True)

    assert len(rows) == 1
    assert rows[0]["source_id"] == "src-001"
    db.close()


def test_delete_source_supprime_la_ligne() -> None:
    """La suppression doit retirer la source de la table."""
    db, registry = _make_registry()
    registry.create_source(_payload())

    registry.delete_source("src-001")

    assert registry.get_source("src-001") is None
    db.close()
