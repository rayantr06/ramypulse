"""Tests TDD pour l'infrastructure SQLite de RamyPulse."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import SQLITE_DB_PATH  # noqa: E402
from core.database import DatabaseManager  # noqa: E402


EXPECTED_TABLES = {
    "clients",
    "source_registry",
    "sources",
    "source_sync_runs",
    "raw_documents",
    "normalized_records",
    "enriched_signals",
    "products",
    "regions",
    "distributors",
    "wilayas",
    "competitors",
    "watchlists",
    "watchlist_metric_snapshots",
    "campaigns",
    "campaign_metrics_snapshots",
    "campaign_signal_links",
    "alert_rules",
    "alerts",
    "client_agent_config",
    "recommendations",
    "creator_profiles",
    "notifications",
    "source_health_snapshots",
    "audit_log",
    "platform_credentials",
    "campaign_posts",
    "post_engagement_metrics",
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


def test_database_cree_les_tables_du_prd() -> None:
    """La création de schéma doit matérialiser toutes les tables attendues."""
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


def test_alerts_watchlist_id_nullable() -> None:
    """La table alerts doit avoir watchlist_id nullable (schema Wave 5, sans FK hard)."""
    db = DatabaseManager(":memory:")
    db.create_tables()

    cols = {row["name"]: row for row in db.connection.execute("PRAGMA table_info(alerts)").fetchall()}
    assert "watchlist_id" in cols, "La colonne watchlist_id doit exister dans alerts"
    # Wave 5 : watchlist_id est nullable — pas de NOT NULL
    assert cols["watchlist_id"]["notnull"] == 0, "watchlist_id doit être nullable (Wave 5)"
    db.close()


def test_alerts_watchlist_id_sans_fk_forcee() -> None:
    """Le schema Wave 5 ne doit pas recreer de FK SQLite sur alerts.watchlist_id."""
    db = DatabaseManager(":memory:")
    db.create_tables()

    foreign_keys = db.connection.execute("PRAGMA foreign_key_list(alerts)").fetchall()

    assert foreign_keys == []
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


def test_create_tables_migre_ancien_schema_recommendations_vers_wave5(tmp_path) -> None:
    """La migration recommendations doit preservеr les donnees legacy et supprimer la table temporaire."""
    db_path = tmp_path / "legacy_recommendations.db"
    db = DatabaseManager(db_path)
    connection = db.connection

    connection.execute(
        """
        CREATE TABLE recommendations (
            recommendation_id TEXT PRIMARY KEY,
            alert_id TEXT,
            signal_type TEXT NOT NULL,
            problem TEXT NOT NULL,
            evidence_summary TEXT,
            urgency TEXT NOT NULL,
            actions TEXT NOT NULL,
            assumptions TEXT,
            risks TEXT,
            confidence TEXT NOT NULL,
            generation_mode TEXT NOT NULL,
            requires_human_validation BOOLEAN DEFAULT TRUE,
            is_validated BOOLEAN DEFAULT FALSE,
            validated_by TEXT,
            validated_at DATETIME,
            feedback TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    connection.execute(
        """
        INSERT INTO recommendations (
            recommendation_id,
            alert_id,
            signal_type,
            problem,
            evidence_summary,
            urgency,
            actions,
            confidence,
            generation_mode,
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "rec-001",
            "alert-001",
            "alert",
            "Le packaging se degrade",
            "Volume negatif en hausse",
            "high",
            "Renforcer la communication packaging",
            "medium",
            "manual_rules",
            "2026-04-01T09:00:00",
        ),
    )
    connection.commit()

    db.create_tables()

    columns = _column_definitions(db, "recommendations")
    tables = _table_names(db)
    migrated = db.connection.execute(
        """
        SELECT recommendation_id, alert_id, trigger_type, analysis_summary,
               recommendations, provider_used, created_at
        FROM recommendations
        WHERE recommendation_id = ?
        """,
        ("rec-001",),
    ).fetchone()

    assert "trigger_type" in columns
    assert "recommendations_legacy" not in tables
    assert migrated is not None
    assert migrated["recommendation_id"] == "rec-001"
    assert migrated["alert_id"] == "alert-001"
    assert migrated["trigger_type"] == "manual"
    assert migrated["analysis_summary"] == "Le packaging se degrade"
    assert migrated["recommendations"] == '["Renforcer la communication packaging"]'
    assert migrated["provider_used"] == "manual_rules"
    assert migrated["created_at"] == "2026-04-01T09:00:00"

    db.close()


def test_create_tables_migre_watchlists_legacy_vers_wave5(tmp_path) -> None:
    """La migration watchlists doit realigner l'ancien schema main vers Wave 5."""
    db_path = tmp_path / "legacy_watchlists.db"
    db = DatabaseManager(db_path)
    connection = db.connection

    connection.execute(
        """
        CREATE TABLE watchlists (
            watchlist_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            scope_type TEXT NOT NULL,
            products TEXT,
            competitors TEXT,
            wilayas TEXT,
            channels TEXT,
            aspects TEXT,
            keywords TEXT,
            source_registry_ids TEXT,
            metric_type TEXT NOT NULL,
            baseline_window INTEGER DEFAULT 30,
            alert_threshold REAL,
            alert_direction TEXT,
            owner TEXT,
            is_active BOOLEAN DEFAULT TRUE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME
        )
        """
    )
    connection.execute(
        """
        INSERT INTO watchlists (
            watchlist_id, name, description, scope_type, products, wilayas,
            channels, aspects, baseline_window, is_active, created_at, updated_at,
            metric_type
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "wl-001",
            "Legacy Oran",
            "description",
            "region",
            '["ramy_citron", "ramy_orange"]',
            '["oran", "tlemcen"]',
            '["google_maps", "facebook"]',
            '["disponibilité", "prix"]',
            14,
            1,
            "2026-03-01T10:00:00",
            "2026-03-02T10:00:00",
            "nss_aspect",
        ),
    )
    connection.commit()

    db.create_tables()

    columns = _column_definitions(db, "watchlists")
    migrated = db.connection.execute(
        """
        SELECT watchlist_id, client_id, watchlist_name, description, scope_type, filters, is_active
        FROM watchlists
        WHERE watchlist_id = ?
        """,
        ("wl-001",),
    ).fetchone()

    assert "watchlist_name" in columns
    assert "filters" in columns
    assert migrated is not None
    assert migrated["client_id"] == "ramy_client_001"
    assert migrated["watchlist_name"] == "Legacy Oran"
    assert migrated["scope_type"] == "region"
    assert migrated["is_active"] == 1
    assert migrated["filters"] == (
        '{"channel": "google_maps", "aspect": "disponibilité", '
        '"wilaya": "oran", "product": "ramy_citron", "sentiment": null, '
        '"period_days": 14, "min_volume": 10}'
    )
    db.close()


def test_create_tables_migre_campaigns_legacy_vers_wave5(tmp_path) -> None:
    """La migration campaigns doit realigner l'ancien schema main vers Wave 5."""
    db_path = tmp_path / "legacy_campaigns.db"
    db = DatabaseManager(db_path)
    connection = db.connection

    connection.execute(
        """
        CREATE TABLE campaigns (
            campaign_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            event_type TEXT NOT NULL,
            brand TEXT NOT NULL,
            products TEXT,
            wilayas TEXT,
            channels TEXT,
            start_at DATETIME NOT NULL,
            end_at DATETIME,
            goal TEXT,
            budget REAL,
            hashtags TEXT,
            keywords TEXT,
            tracked_accounts TEXT,
            tracked_posts TEXT,
            tracked_urls TEXT,
            creator_profiles TEXT,
            before_window INTEGER DEFAULT 30,
            after_window INTEGER DEFAULT 14,
            status TEXT DEFAULT 'draft',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME
        )
        """
    )
    connection.execute(
        """
        INSERT INTO campaigns (
            campaign_id, name, event_type, products, wilayas, channels, start_at,
            end_at, goal, budget, keywords, before_window, after_window, status,
            brand, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "camp-001",
            "Legacy Campaign",
            "promotion",
            '["ramy_citron"]',
            '["oran", "tlemcen"]',
            '["instagram", "facebook"]',
            "2026-03-01T08:00:00",
            "2026-03-15T22:00:00",
            "Boost awareness",
            125000.0,
            '["ramy", "promo"]',
            10,
            7,
            "active",
            "Ramy",
            "2026-02-20T10:00:00",
            "2026-02-21T10:00:00",
        ),
    )
    connection.commit()

    db.create_tables()

    migrated = db.connection.execute(
        """
        SELECT campaign_id, client_id, campaign_name, campaign_type, platform,
               description, target_regions, keywords, start_date, end_date,
               pre_window_days, post_window_days, status
        FROM campaigns
        WHERE campaign_id = ?
        """,
        ("camp-001",),
    ).fetchone()

    assert migrated is not None
    assert migrated["client_id"] == "ramy_client_001"
    assert migrated["campaign_name"] == "Legacy Campaign"
    assert migrated["campaign_type"] == "promotion"
    assert migrated["platform"] == "multi_platform"
    assert migrated["description"] == "Boost awareness"
    assert migrated["target_regions"] == '["oran", "tlemcen"]'
    assert migrated["keywords"] == '["ramy", "promo"]'
    assert migrated["start_date"] == "2026-03-01"
    assert migrated["end_date"] == "2026-03-15"
    assert migrated["pre_window_days"] == 10
    assert migrated["post_window_days"] == 7
    assert migrated["status"] == "active"
    db.close()


def test_create_tables_migre_alerts_legacy_vers_wave5(tmp_path) -> None:
    """La migration alerts doit convertir le payload legacy vers le schema Wave 5."""
    db_path = tmp_path / "legacy_alerts.db"
    db = DatabaseManager(db_path)
    connection = db.connection

    connection.execute(
        """
        CREATE TABLE alerts (
            alert_id TEXT PRIMARY KEY,
            watchlist_id TEXT NOT NULL,
            alert_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            metric_name TEXT,
            metric_value REAL,
            baseline_value REAL,
            delta REAL,
            evidence TEXT,
            is_acknowledged BOOLEAN DEFAULT FALSE,
            acknowledged_by TEXT,
            acknowledged_at DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    connection.execute(
        """
        INSERT INTO alerts (
            alert_id, watchlist_id, alert_type, severity, title, description,
            metric_name, metric_value, baseline_value, delta, evidence,
            is_acknowledged, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "alert-001",
            "wl-001",
            "volume_drop",
            "high",
            "Volume en baisse",
            "description",
            "volume",
            21.0,
            42.0,
            -21.0,
            "evidence",
            1,
            "2026-03-21T10:00:00",
        ),
    )
    connection.commit()

    db.create_tables()

    migrated = db.connection.execute(
        """
        SELECT alert_id, client_id, watchlist_id, alert_rule_id, status, detected_at,
               alert_payload, dedup_key, navigation_url
        FROM alerts
        WHERE alert_id = ?
        """,
        ("alert-001",),
    ).fetchone()

    assert migrated is not None
    assert migrated["client_id"] == "ramy_client_001"
    assert migrated["watchlist_id"] == "wl-001"
    assert migrated["alert_rule_id"] == "volume_drop"
    assert migrated["status"] == "acknowledged"
    assert migrated["detected_at"] == "2026-03-21T10:00:00"
    assert migrated["dedup_key"] is None
    assert migrated["navigation_url"] is None
    assert migrated["alert_payload"] == (
        '{"metric_name": "volume", "metric_value": 21.0, "baseline_value": 42.0, '
        '"delta": -21.0, "evidence": "evidence"}'
    )
    db.close()


def test_create_tables_migre_notifications_legacy_vers_wave5(tmp_path) -> None:
    """La migration notifications doit realigner body/is_read/reference_id."""
    db_path = tmp_path / "legacy_notifications.db"
    db = DatabaseManager(db_path)
    connection = db.connection

    connection.execute(
        """
        CREATE TABLE notifications (
            notification_id TEXT PRIMARY KEY,
            alert_id TEXT,
            recommendation_id TEXT,
            channel TEXT NOT NULL,
            recipient TEXT,
            title TEXT NOT NULL,
            body TEXT,
            is_read BOOLEAN DEFAULT FALSE,
            delivered_at DATETIME,
            read_at DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    connection.execute(
        """
        INSERT INTO notifications (
            notification_id, alert_id, recommendation_id, channel, recipient,
            title, body, is_read, delivered_at, read_at, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "notif-001",
            "alert-001",
            None,
            "email",
            "ops@example.test",
            "Titre",
            "Message",
            1,
            "2026-03-21T10:05:00",
            "2026-03-21T10:06:00",
            "2026-03-21T10:00:00",
        ),
    )
    connection.commit()

    db.create_tables()

    migrated = db.connection.execute(
        """
        SELECT notification_id, client_id, notification_type, reference_id, title,
               message, channel, status, created_at, read_at
        FROM notifications
        WHERE notification_id = ?
        """,
        ("notif-001",),
    ).fetchone()

    assert migrated is not None
    assert migrated["client_id"] == "ramy_client_001"
    assert migrated["notification_type"] == "alert"
    assert migrated["reference_id"] == "alert-001"
    assert migrated["message"] == "Message"
    assert migrated["channel"] == "email"
    assert migrated["status"] == "read"
    assert migrated["read_at"] == "2026-03-21T10:06:00"
    assert migrated["created_at"] == "2026-03-21T10:00:00"
    db.close()
