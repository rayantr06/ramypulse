"""Tests TDD pour l'infrastructure SQLite de RamyPulse."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import SQLITE_DB_PATH  # noqa: E402
from core.database import DatabaseManager  # noqa: E402


EXPECTED_TABLES = {
    "source_registry",
    "products",
    "wilayas",
    "competitors",
    "watchlists",
    "campaigns",
    "alerts",
    "recommendations",
    "creator_profiles",
    "notifications",
    "audit_log",
}


def _table_names(db: DatabaseManager) -> set[str]:
    """Retourne les noms de tables utilisateur présentes dans la base."""
    rows = db.connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
        """
    ).fetchall()
    return {row["name"] for row in rows}


def test_sqlite_db_path_est_defini_dans_config() -> None:
    """config.py doit exposer SQLITE_DB_PATH sous data/ramypulse.db."""
    assert SQLITE_DB_PATH.name == "ramypulse.db"
    assert SQLITE_DB_PATH.parent.name == "data"


def test_database_manager_supporte_memory() -> None:
    """La base :memory: doit être supportée pour les tests."""
    db = DatabaseManager(":memory:")
    assert db.db_path == ":memory:"
    db.close()


def test_database_cree_les_11_tables_du_prd() -> None:
    """La création de schéma doit matérialiser les 11 tables attendues."""
    db = DatabaseManager(":memory:")
    db.create_tables()

    assert _table_names(db) == EXPECTED_TABLES
    db.close()


def test_create_tables_est_idempotent() -> None:
    """Deux appels successifs à create_tables() ne doivent pas échouer."""
    db = DatabaseManager(":memory:")
    db.create_tables()
    db.create_tables()

    assert _table_names(db) == EXPECTED_TABLES
    db.close()


def test_connection_utilise_sqlite_row() -> None:
    """Les résultats doivent être accessibles par nom de colonne."""
    db = DatabaseManager(":memory:")
    row = db.connection.execute("SELECT 1 AS value").fetchone()

    assert row["value"] == 1
    db.close()


def test_foreign_keys_activees() -> None:
    """La connexion doit activer les foreign keys SQLite."""
    db = DatabaseManager(":memory:")
    row = db.connection.execute("PRAGMA foreign_keys").fetchone()

    assert row[0] == 1
    db.close()


def test_alerts_reference_watchlists() -> None:
    """La table alerts doit porter une clé étrangère vers watchlists."""
    db = DatabaseManager(":memory:")
    db.create_tables()

    rows = db.connection.execute("PRAGMA foreign_key_list(alerts)").fetchall()
    references = {(row["table"], row["from"], row["to"]) for row in rows}

    assert ("watchlists", "watchlist_id", "watchlist_id") in references
    db.close()


def test_notifications_et_audit_log_existants() -> None:
    """Le schéma doit inclure notifications et audit_log."""
    db = DatabaseManager(":memory:")
    db.create_tables()

    tables = _table_names(db)
    assert "notifications" in tables
    assert "audit_log" in tables
    db.close()
