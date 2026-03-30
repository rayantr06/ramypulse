"""Tests TDD pour l'infrastructure SQLite de RamyPulse."""

from __future__ import annotations

import sys
from pathlib import Path

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


def _column_definitions(db: DatabaseManager, table_name: str) -> dict[str, str]:
    """Retourne les types déclarés des colonnes d'une table SQLite."""
    rows = db.connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row["name"]: row["type"] for row in rows}


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


def test_products_schema_aligne_prd_v6() -> None:
    """La table products doit utiliser un product_id textuel."""
    db = DatabaseManager(":memory:")
    db.create_tables()

    columns = _column_definitions(db, "products")

    assert columns["product_id"] == "TEXT"
    db.close()


def test_wilayas_schema_aligne_prd_v6() -> None:
    """La table wilayas doit utiliser les noms de colonnes du PRD v6."""
    db = DatabaseManager(":memory:")
    db.create_tables()

    columns = _column_definitions(db, "wilayas")

    assert "wilaya_name_fr" in columns
    assert "wilaya_name_ar" in columns
    assert "name_fr" not in columns
    assert "name_ar" not in columns
    db.close()


def test_competitors_schema_aligne_prd_v6() -> None:
    """La table competitors doit utiliser un competitor_id textuel."""
    db = DatabaseManager(":memory:")
    db.create_tables()

    columns = _column_definitions(db, "competitors")

    assert columns["competitor_id"] == "TEXT"
    db.close()


def test_create_tables_migre_ancien_schema_vers_prd_v6(tmp_path) -> None:
    """create_tables() doit realigner une base legacy vers le schema PRD."""
    db_path = tmp_path / "legacy.db"
    db = DatabaseManager(db_path)
    connection = db.connection

    connection.execute(
        """
        CREATE TABLE products (
            product_id INTEGER PRIMARY KEY AUTOINCREMENT,
            brand TEXT NOT NULL,
            product_name TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE wilayas (
            wilaya_code TEXT PRIMARY KEY,
            name_fr TEXT NOT NULL,
            name_ar TEXT NOT NULL DEFAULT ''
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE competitors (
            competitor_id INTEGER PRIMARY KEY AUTOINCREMENT,
            brand_name TEXT NOT NULL UNIQUE
        )
        """
    )
    connection.execute(
        "INSERT INTO products (brand, product_name) VALUES (?, ?)",
        ("Ramy", "Jus orange"),
    )
    connection.execute(
        "INSERT INTO wilayas (wilaya_code, name_fr, name_ar) VALUES (?, ?, ?)",
        ("06", "Bejaia", "بجاية"),
    )
    connection.execute(
        "INSERT INTO competitors (brand_name) VALUES (?)",
        ("Ifri",),
    )
    connection.commit()

    db.create_tables()

    assert _column_definitions(db, "products")["product_id"] == "TEXT"
    assert "wilaya_name_fr" in _column_definitions(db, "wilayas")
    assert _column_definitions(db, "competitors")["competitor_id"] == "TEXT"

    migrated_product = db.connection.execute(
        "SELECT product_id, brand, product_name FROM products"
    ).fetchone()
    migrated_wilaya = db.connection.execute(
        "SELECT wilaya_code, wilaya_name_fr, wilaya_name_ar FROM wilayas"
    ).fetchone()
    migrated_competitor = db.connection.execute(
        "SELECT competitor_id, brand_name FROM competitors"
    ).fetchone()

    assert migrated_product["brand"] == "Ramy"
    assert migrated_product["product_name"] == "Jus orange"
    assert migrated_product["product_id"]
    assert migrated_wilaya["wilaya_name_fr"] == "Bejaia"
    assert migrated_wilaya["wilaya_name_ar"] == "بجاية"
    assert migrated_competitor["brand_name"] == "Ifri"
    assert migrated_competitor["competitor_id"]

    db.close()
