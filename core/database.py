"""Infrastructure SQLite locale pour les objets metier RamyPulse.

Expose un gestionnaire unique compatible avec les besoins de l'infrastructure
Phase 1 et des catalogues metier.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path

from config import (
    DEFAULT_AGENT_MODEL,
    DEFAULT_AGENT_PROVIDER,
    DEFAULT_CLIENT_ID,
    SQLITE_DB_PATH,
)

logger = logging.getLogger(__name__)


_SCHEMA_STATEMENTS = {
    "clients": """
        CREATE TABLE IF NOT EXISTS clients (
            client_id TEXT PRIMARY KEY,
            client_name TEXT NOT NULL,
            industry TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """,
    "source_registry": """
        CREATE TABLE IF NOT EXISTS source_registry (
            source_id TEXT PRIMARY KEY,
            platform TEXT NOT NULL,
            source_type TEXT NOT NULL,
            display_name TEXT NOT NULL,
            external_id TEXT,
            url TEXT,
            owner_type TEXT NOT NULL,
            auth_mode TEXT,
            brand TEXT,
            is_active BOOLEAN DEFAULT TRUE,
            sync_frequency TEXT,
            last_sync_at DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME
        )
    """,
    "sources": """
        CREATE TABLE IF NOT EXISTS sources (
            source_id TEXT PRIMARY KEY,
            client_id TEXT NOT NULL DEFAULT 'ramy_client_001',
            source_name TEXT NOT NULL,
            platform TEXT NOT NULL,
            source_type TEXT NOT NULL,
            owner_type TEXT NOT NULL,
            auth_mode TEXT,
            config_json TEXT DEFAULT '{}',
            is_active INTEGER NOT NULL DEFAULT 1,
            sync_frequency_minutes INTEGER DEFAULT 60,
            freshness_sla_hours INTEGER DEFAULT 24,
            last_sync_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """,
    "source_sync_runs": """
        CREATE TABLE IF NOT EXISTS source_sync_runs (
            sync_run_id TEXT PRIMARY KEY,
            source_id TEXT NOT NULL,
            run_mode TEXT NOT NULL,
            status TEXT NOT NULL,
            records_fetched INTEGER DEFAULT 0,
            records_inserted INTEGER DEFAULT 0,
            records_failed INTEGER DEFAULT 0,
            error_message TEXT,
            started_at TEXT NOT NULL,
            ended_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """,
    "raw_documents": """
        CREATE TABLE IF NOT EXISTS raw_documents (
            raw_document_id TEXT PRIMARY KEY,
            client_id TEXT NOT NULL DEFAULT 'ramy_client_001',
            source_id TEXT NOT NULL,
            sync_run_id TEXT,
            external_document_id TEXT,
            raw_payload TEXT,
            raw_text TEXT,
            raw_metadata TEXT DEFAULT '{}',
            checksum_sha256 TEXT,
            collected_at TEXT NOT NULL,
            is_normalized INTEGER DEFAULT 0,
            normalizer_version TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """,
    "normalized_records": """
        CREATE TABLE IF NOT EXISTS normalized_records (
            normalized_record_id TEXT PRIMARY KEY,
            client_id TEXT NOT NULL DEFAULT 'ramy_client_001',
            source_id TEXT NOT NULL,
            raw_document_id TEXT,
            text TEXT,
            text_original TEXT,
            channel TEXT,
            source_url TEXT,
            published_at TEXT,
            language TEXT,
            script_detected TEXT,
            normalized_payload TEXT DEFAULT '{}',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """,
    "enriched_signals": """
        CREATE TABLE IF NOT EXISTS enriched_signals (
            signal_id TEXT PRIMARY KEY,
            client_id TEXT NOT NULL DEFAULT 'ramy_client_001',
            normalized_record_id TEXT NOT NULL,
            source_id TEXT,
            sentiment_label TEXT,
            confidence REAL,
            aspect TEXT,
            aspects TEXT DEFAULT '[]',
            aspect_sentiments TEXT DEFAULT '[]',
            brand TEXT,
            competitor TEXT,
            product TEXT,
            product_line TEXT,
            sku TEXT,
            wilaya TEXT,
            region_id TEXT,
            distributor_id TEXT,
            source_url TEXT,
            channel TEXT,
            event_timestamp TEXT,
            normalizer_version TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """,
    "products": """
        CREATE TABLE IF NOT EXISTS products (
            product_id TEXT PRIMARY KEY,
            brand TEXT NOT NULL,
            product_line TEXT NOT NULL DEFAULT '',
            product_name TEXT NOT NULL,
            sku TEXT UNIQUE,
            category TEXT NOT NULL DEFAULT '',
            keywords_ar TEXT NOT NULL DEFAULT '[]',
            keywords_arabizi TEXT NOT NULL DEFAULT '[]',
            keywords_fr TEXT NOT NULL DEFAULT '[]',
            is_active BOOLEAN DEFAULT TRUE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """,
    "regions": """
        CREATE TABLE IF NOT EXISTS regions (
            region_id TEXT PRIMARY KEY,
            client_id TEXT NOT NULL DEFAULT 'ramy_client_001',
            region_name TEXT NOT NULL,
            region_code TEXT,
            wilayas_json TEXT DEFAULT '[]',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """,
    "distributors": """
        CREATE TABLE IF NOT EXISTS distributors (
            distributor_id TEXT PRIMARY KEY,
            client_id TEXT NOT NULL DEFAULT 'ramy_client_001',
            distributor_name TEXT NOT NULL,
            region_id TEXT,
            distributor_type TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """,
    "wilayas": """
        CREATE TABLE IF NOT EXISTS wilayas (
            wilaya_code TEXT PRIMARY KEY,
            wilaya_name_fr TEXT NOT NULL,
            wilaya_name_ar TEXT NOT NULL DEFAULT '',
            keywords_arabizi TEXT NOT NULL DEFAULT '[]',
            region TEXT NOT NULL DEFAULT ''
        )
    """,
    "competitors": """
        CREATE TABLE IF NOT EXISTS competitors (
            competitor_id TEXT PRIMARY KEY,
            brand_name TEXT NOT NULL UNIQUE,
            category TEXT NOT NULL DEFAULT '',
            keywords_ar TEXT NOT NULL DEFAULT '[]',
            keywords_arabizi TEXT NOT NULL DEFAULT '[]',
            keywords_fr TEXT NOT NULL DEFAULT '[]',
            is_active BOOLEAN DEFAULT TRUE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """,
    "watchlists": """
        CREATE TABLE IF NOT EXISTS watchlists (
            watchlist_id      TEXT PRIMARY KEY,
            client_id         TEXT NOT NULL DEFAULT 'ramy_client_001',
            watchlist_name    TEXT NOT NULL,
            description       TEXT,
            scope_type        TEXT,
            filters           TEXT,
            is_active         INTEGER DEFAULT 1,
            created_at        TEXT,
            updated_at        TEXT
        )
    """,
    "watchlist_metric_snapshots": """
        CREATE TABLE IF NOT EXISTS watchlist_metric_snapshots (
            snapshot_id        TEXT PRIMARY KEY,
            watchlist_id       TEXT NOT NULL,
            nss_current        REAL,
            nss_previous       REAL,
            volume_current     INTEGER DEFAULT 0,
            volume_previous    INTEGER DEFAULT 0,
            delta_nss          REAL,
            delta_volume_pct   REAL,
            aspect_breakdown   TEXT DEFAULT '{}',
            computed_at        TEXT NOT NULL
        )
    """,
    "campaigns": """
        CREATE TABLE IF NOT EXISTS campaigns (
            campaign_id       TEXT PRIMARY KEY,
            client_id         TEXT NOT NULL DEFAULT 'ramy_client_001',
            campaign_name     TEXT NOT NULL,
            campaign_type     TEXT,
            platform          TEXT,
            description       TEXT,
            influencer_handle TEXT,
            influencer_tier   TEXT,
            target_segment    TEXT,
            target_aspects    TEXT,
            target_regions    TEXT,
            keywords          TEXT,
            budget_dza        INTEGER,
            start_date        TEXT,
            end_date          TEXT,
            pre_window_days   INTEGER DEFAULT 14,
            post_window_days  INTEGER DEFAULT 14,
            status            TEXT DEFAULT 'planned',
            created_at        TEXT,
            updated_at        TEXT
        )
    """,
    "campaign_metrics_snapshots": """
        CREATE TABLE IF NOT EXISTS campaign_metrics_snapshots (
            snapshot_id         TEXT PRIMARY KEY,
            campaign_id         TEXT NOT NULL,
            phase               TEXT NOT NULL,
            metric_date         TEXT NOT NULL,
            nss_filtered        REAL,
            nss_baseline        REAL,
            nss_uplift          REAL,
            volume_filtered     INTEGER DEFAULT 0,
            volume_baseline     INTEGER DEFAULT 0,
            volume_lift_pct     REAL,
            aspect_breakdown    TEXT DEFAULT '{}',
            sentiment_breakdown TEXT DEFAULT '{}',
            computed_at         TEXT NOT NULL,
            UNIQUE(campaign_id, phase, metric_date)
        )
    """,
    "campaign_signal_links": """
        CREATE TABLE IF NOT EXISTS campaign_signal_links (
            link_id             TEXT PRIMARY KEY,
            campaign_id         TEXT NOT NULL,
            signal_id           TEXT NOT NULL,
            phase               TEXT NOT NULL,
            attribution_score   REAL,
            attributed_at       TEXT NOT NULL
        )
    """,
    "alert_rules": """
        CREATE TABLE IF NOT EXISTS alert_rules (
            alert_rule_id       TEXT PRIMARY KEY,
            client_id           TEXT NOT NULL DEFAULT 'ramy_client_001',
            watchlist_id        TEXT,
            rule_name           TEXT NOT NULL,
            rule_type           TEXT NOT NULL,
            threshold_value     REAL,
            comparator          TEXT,
            lookback_window     TEXT,
            severity_level      TEXT NOT NULL,
            is_active           INTEGER NOT NULL DEFAULT 1
        )
    """,
    "alerts": """
        CREATE TABLE IF NOT EXISTS alerts (
            alert_id          TEXT PRIMARY KEY,
            client_id         TEXT NOT NULL DEFAULT 'ramy_client_001',
            watchlist_id      TEXT,
            alert_rule_id     TEXT,
            title             TEXT NOT NULL,
            description       TEXT,
            severity          TEXT,
            status            TEXT DEFAULT 'new',
            detected_at       TEXT,
            resolved_at       TEXT,
            alert_payload     TEXT,
            dedup_key         TEXT,
            navigation_url    TEXT
        )
    """,
    "client_agent_config": """
        CREATE TABLE IF NOT EXISTS client_agent_config (
            config_id               TEXT PRIMARY KEY,
            client_id               TEXT NOT NULL UNIQUE DEFAULT 'ramy_client_001',
            provider                TEXT NOT NULL DEFAULT 'ollama_local',
            model                   TEXT,
            api_key_encrypted       TEXT,
            auto_trigger_on_alert   INTEGER NOT NULL DEFAULT 0,
            auto_trigger_severity   TEXT DEFAULT 'critical',
            weekly_report_enabled   INTEGER NOT NULL DEFAULT 0,
            weekly_report_day       INTEGER DEFAULT 1,
            created_at              TEXT NOT NULL,
            updated_at              TEXT NOT NULL
        )
    """,
    "recommendations": """
        CREATE TABLE IF NOT EXISTS recommendations (
            recommendation_id TEXT PRIMARY KEY,
            client_id         TEXT NOT NULL DEFAULT 'ramy_client_001',
            trigger_type      TEXT,
            trigger_id        TEXT,
            alert_id          TEXT,
            analysis_summary  TEXT,
            recommendations   TEXT,
            watchlist_priorities TEXT,
            confidence_score  REAL,
            data_quality_note TEXT,
            provider_used     TEXT,
            model_used        TEXT,
            context_tokens    INTEGER,
            generation_ms     INTEGER,
            status            TEXT DEFAULT 'active',
            created_at        TEXT
        )
    """,
    "creator_profiles": """
        CREATE TABLE IF NOT EXISTS creator_profiles (
            creator_id TEXT PRIMARY KEY,
            display_name TEXT NOT NULL,
            platform TEXT NOT NULL,
            external_id TEXT,
            profile_url TEXT,
            category TEXT,
            estimated_reach TEXT,
            contact_info TEXT,
            is_active BOOLEAN DEFAULT TRUE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """,
    "notifications": """
        CREATE TABLE IF NOT EXISTS notifications (
            notification_id   TEXT PRIMARY KEY,
            client_id         TEXT NOT NULL DEFAULT 'ramy_client_001',
            notification_type TEXT,
            reference_id      TEXT,
            title             TEXT NOT NULL,
            message           TEXT,
            channel           TEXT,
            status            TEXT DEFAULT 'unread',
            created_at        TEXT,
            read_at           TEXT
        )
    """,
    "source_health_snapshots": """
        CREATE TABLE IF NOT EXISTS source_health_snapshots (
            snapshot_id TEXT PRIMARY KEY,
            source_id TEXT NOT NULL,
            health_score REAL NOT NULL,
            success_rate_pct REAL,
            freshness_hours REAL,
            records_fetched_avg REAL,
            computed_at TEXT NOT NULL
        )
    """,
    "audit_log": """
        CREATE TABLE IF NOT EXISTS audit_log (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            source TEXT,
            details TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """,
}


def _table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
    """Retourne True si une table utilisateur existe deja."""
    row = connection.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table' AND name = ?
        """,
        (table_name,),
    ).fetchone()
    return row is not None


def _column_definitions(
    connection: sqlite3.Connection,
    table_name: str,
) -> dict[str, str]:
    """Retourne les colonnes declarees d'une table SQLite."""
    rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row["name"]: row["type"].upper() for row in rows}


def _legacy_column(columns: dict[str, str], *candidates: str) -> str | None:
    """Retourne le premier nom de colonne existant parmi plusieurs alias."""
    for candidate in candidates:
        if candidate in columns:
            return candidate
    return None


def _id_select_expression(
    columns: dict[str, str],
    column_name: str,
    prefix: str,
) -> str:
    """Construit l'expression SQL de migration d'un identifiant legacy."""
    if column_name not in columns:
        return f"'{prefix}-' || lower(hex(randomblob(6)))"
    if columns[column_name] == "TEXT":
        return column_name
    return f"'{prefix}-' || {column_name}"


def _select_or_default(
    columns: dict[str, str],
    column_name: str,
    default_sql: str,
) -> str:
    """Selectionne une colonne si elle existe, sinon une valeur par defaut."""
    return column_name if column_name in columns else default_sql


def _deserialize_json_list(value: object) -> list[str]:
    """Retourne une liste de chaines depuis une valeur JSON ou scalaire."""
    if value in (None, ""):
        return []
    if isinstance(value, list):
        return [str(item) for item in value if item not in (None, "")]
    if isinstance(value, tuple):
        return [str(item) for item in value if item not in (None, "")]
    if isinstance(value, str):
        try:
            payload = json.loads(value)
        except json.JSONDecodeError:
            payload = value
        if isinstance(payload, list):
            return [str(item) for item in payload if item not in (None, "")]
        if payload in (None, ""):
            return []
        return [str(payload)]
    return [str(value)]


def _serialize_json_list(values: list[str]) -> str:
    """Serialise une liste pour stockage SQLite."""
    return json.dumps(values, ensure_ascii=False)


def _serialize_json_dict(payload: dict[str, object]) -> str:
    """Serialise un dictionnaire pour stockage SQLite."""
    return json.dumps(payload, ensure_ascii=False)


def _first_json_value(value: object) -> str | None:
    """Retourne la premiere valeur utile d'une liste JSON."""
    items = _deserialize_json_list(value)
    return items[0] if items else None


def _to_iso_date(value: object) -> str | None:
    """Convertit une date legacy en format YYYY-MM-DD."""
    if value in (None, ""):
        return None
    text = str(value)
    return text[:10]


def _migrate_products_if_needed(connection: sqlite3.Connection) -> None:
    """Migre la table products vers le contrat PRD si necessaire."""
    if not _table_exists(connection, "products"):
        return

    columns = _column_definitions(connection, "products")
    if columns.get("product_id") == "TEXT":
        return

    logger.info("Migration SQLite : realignement de la table products")
    connection.execute("ALTER TABLE products RENAME TO products_legacy")
    connection.execute(_SCHEMA_STATEMENTS["products"])
    connection.execute(
        f"""
        INSERT INTO products (
            product_id,
            brand,
            product_line,
            product_name,
            sku,
            category,
            keywords_ar,
            keywords_arabizi,
            keywords_fr,
            is_active,
            created_at
        )
        SELECT
            {_id_select_expression(columns, "product_id", "prod")},
            {_select_or_default(columns, "brand", "''")},
            {_select_or_default(columns, "product_line", "''")},
            {_select_or_default(columns, "product_name", "''")},
            {_select_or_default(columns, "sku", "NULL")},
            {_select_or_default(columns, "category", "''")},
            {_select_or_default(columns, "keywords_ar", "'[]'")},
            {_select_or_default(columns, "keywords_arabizi", "'[]'")},
            {_select_or_default(columns, "keywords_fr", "'[]'")},
            {_select_or_default(columns, "is_active", "1")},
            {_select_or_default(columns, "created_at", "CURRENT_TIMESTAMP")}
        FROM products_legacy
        """
    )
    connection.execute("DROP TABLE products_legacy")


def _migrate_wilayas_if_needed(connection: sqlite3.Connection) -> None:
    """Migre la table wilayas vers le contrat PRD si necessaire."""
    if not _table_exists(connection, "wilayas"):
        return

    columns = _column_definitions(connection, "wilayas")
    if "wilaya_name_fr" in columns and "wilaya_name_ar" in columns:
        return

    logger.info("Migration SQLite : realignement de la table wilayas")
    connection.execute("ALTER TABLE wilayas RENAME TO wilayas_legacy")
    connection.execute(_SCHEMA_STATEMENTS["wilayas"])

    name_fr_column = _legacy_column(columns, "wilaya_name_fr", "name_fr")
    name_ar_column = _legacy_column(columns, "wilaya_name_ar", "name_ar")

    connection.execute(
        f"""
        INSERT INTO wilayas (
            wilaya_code,
            wilaya_name_fr,
            wilaya_name_ar,
            keywords_arabizi,
            region
        )
        SELECT
            {_select_or_default(columns, "wilaya_code", "''")},
            {_select_or_default(columns, name_fr_column or "", "''")},
            {_select_or_default(columns, name_ar_column or "", "''")},
            {_select_or_default(columns, "keywords_arabizi", "'[]'")},
            {_select_or_default(columns, "region", "''")}
        FROM wilayas_legacy
        """
    )
    connection.execute("DROP TABLE wilayas_legacy")


def _migrate_competitors_if_needed(connection: sqlite3.Connection) -> None:
    """Migre la table competitors vers le contrat PRD si necessaire."""
    if not _table_exists(connection, "competitors"):
        return

    columns = _column_definitions(connection, "competitors")
    if columns.get("competitor_id") == "TEXT":
        return

    logger.info("Migration SQLite : realignement de la table competitors")
    connection.execute("ALTER TABLE competitors RENAME TO competitors_legacy")
    connection.execute(_SCHEMA_STATEMENTS["competitors"])
    connection.execute(
        f"""
        INSERT INTO competitors (
            competitor_id,
            brand_name,
            category,
            keywords_ar,
            keywords_arabizi,
            keywords_fr,
            is_active,
            created_at
        )
        SELECT
            {_id_select_expression(columns, "competitor_id", "comp")},
            {_select_or_default(columns, "brand_name", "''")},
            {_select_or_default(columns, "category", "''")},
            {_select_or_default(columns, "keywords_ar", "'[]'")},
            {_select_or_default(columns, "keywords_arabizi", "'[]'")},
            {_select_or_default(columns, "keywords_fr", "'[]'")},
            {_select_or_default(columns, "is_active", "1")},
            {_select_or_default(columns, "created_at", "CURRENT_TIMESTAMP")}
        FROM competitors_legacy
        """
    )
    connection.execute("DROP TABLE competitors_legacy")


def _migrate_watchlists_if_needed(connection: sqlite3.Connection) -> None:
    """Migre la table watchlists du schema legacy main vers Wave 5."""
    if not _table_exists(connection, "watchlists"):
        return

    columns = _column_definitions(connection, "watchlists")
    if "watchlist_name" in columns and "filters" in columns and "client_id" in columns:
        return

    logger.info("Migration SQLite : realignement de la table watchlists vers schema Wave 5")
    rows = [dict(row) for row in connection.execute("SELECT * FROM watchlists").fetchall()]
    connection.execute("ALTER TABLE watchlists RENAME TO watchlists_legacy")
    connection.execute(_SCHEMA_STATEMENTS["watchlists"])

    for row in rows:
        filters = {
            "channel": _first_json_value(row.get("channels")),
            "aspect": _first_json_value(row.get("aspects")),
            "wilaya": _first_json_value(row.get("wilayas")),
            "product": _first_json_value(row.get("products")),
            "sentiment": None,
            "period_days": int(row.get("baseline_window") or 7),
            "min_volume": 10,
        }
        connection.execute(
            """
            INSERT INTO watchlists (
                watchlist_id,
                client_id,
                watchlist_name,
                description,
                scope_type,
                filters,
                is_active,
                created_at,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row.get("watchlist_id"),
                DEFAULT_CLIENT_ID,
                row.get("name", ""),
                row.get("description"),
                row.get("scope_type"),
                _serialize_json_dict(filters),
                1 if row.get("is_active", 1) else 0,
                row.get("created_at"),
                row.get("updated_at"),
            ),
        )

    connection.execute("DROP TABLE watchlists_legacy")


def _migrate_campaigns_if_needed(connection: sqlite3.Connection) -> None:
    """Migre la table campaigns du schema legacy main vers Wave 5."""
    if not _table_exists(connection, "campaigns"):
        return

    columns = _column_definitions(connection, "campaigns")
    if "campaign_name" in columns and "client_id" in columns:
        return

    logger.info("Migration SQLite : realignement de la table campaigns vers schema Wave 5")
    rows = [dict(row) for row in connection.execute("SELECT * FROM campaigns").fetchall()]
    connection.execute("ALTER TABLE campaigns RENAME TO campaigns_legacy")
    connection.execute(_SCHEMA_STATEMENTS["campaigns"])

    for row in rows:
        channels = _deserialize_json_list(row.get("channels"))
        platform = None
        if len(channels) > 1:
            platform = "multi_platform"
        elif len(channels) == 1:
            platform = channels[0]

        connection.execute(
            """
            INSERT INTO campaigns (
                campaign_id,
                client_id,
                campaign_name,
                campaign_type,
                platform,
                description,
                influencer_handle,
                influencer_tier,
                target_segment,
                target_aspects,
                target_regions,
                keywords,
                budget_dza,
                start_date,
                end_date,
                pre_window_days,
                post_window_days,
                status,
                created_at,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row.get("campaign_id"),
                DEFAULT_CLIENT_ID,
                row.get("name", ""),
                row.get("event_type"),
                platform,
                row.get("goal"),
                None,
                None,
                None,
                _serialize_json_list([]),
                _serialize_json_list(_deserialize_json_list(row.get("wilayas"))),
                _serialize_json_list(_deserialize_json_list(row.get("keywords"))),
                int(row.get("budget")) if row.get("budget") not in (None, "") else None,
                _to_iso_date(row.get("start_at")),
                _to_iso_date(row.get("end_at")),
                int(row.get("before_window") or 14),
                int(row.get("after_window") or 14),
                row.get("status") if row.get("status") not in (None, "", "draft") else "planned",
                row.get("created_at"),
                row.get("updated_at"),
            ),
        )

    connection.execute("DROP TABLE campaigns_legacy")


def _migrate_alerts_if_needed(connection: sqlite3.Connection) -> None:
    """Migre la table alerts du schema legacy main vers Wave 5."""
    if not _table_exists(connection, "alerts"):
        return

    columns = _column_definitions(connection, "alerts")
    if "client_id" in columns and "alert_rule_id" in columns and "alert_payload" in columns:
        return

    logger.info("Migration SQLite : realignement de la table alerts vers schema Wave 5")
    rows = [dict(row) for row in connection.execute("SELECT * FROM alerts").fetchall()]
    connection.execute("ALTER TABLE alerts RENAME TO alerts_legacy")
    connection.execute(_SCHEMA_STATEMENTS["alerts"])

    for row in rows:
        payload = {
            "metric_name": row.get("metric_name"),
            "metric_value": row.get("metric_value"),
            "baseline_value": row.get("baseline_value"),
            "delta": row.get("delta"),
            "evidence": row.get("evidence"),
        }
        status = "acknowledged" if row.get("is_acknowledged") else "new"
        connection.execute(
            """
            INSERT INTO alerts (
                alert_id,
                client_id,
                watchlist_id,
                alert_rule_id,
                title,
                description,
                severity,
                status,
                detected_at,
                resolved_at,
                alert_payload,
                dedup_key,
                navigation_url
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row.get("alert_id"),
                DEFAULT_CLIENT_ID,
                row.get("watchlist_id"),
                row.get("alert_type"),
                row.get("title", ""),
                row.get("description"),
                row.get("severity"),
                status,
                row.get("created_at"),
                None,
                _serialize_json_dict(payload),
                None,
                None,
            ),
        )

    connection.execute("DROP TABLE alerts_legacy")


def _migrate_notifications_if_needed(connection: sqlite3.Connection) -> None:
    """Migre la table notifications du schema legacy main vers Wave 5."""
    if not _table_exists(connection, "notifications"):
        return

    columns = _column_definitions(connection, "notifications")
    if "client_id" in columns and "notification_type" in columns and "message" in columns:
        return

    logger.info("Migration SQLite : realignement de la table notifications vers schema Wave 5")
    rows = [dict(row) for row in connection.execute("SELECT * FROM notifications").fetchall()]
    connection.execute("ALTER TABLE notifications RENAME TO notifications_legacy")
    connection.execute(_SCHEMA_STATEMENTS["notifications"])

    for row in rows:
        reference_id = row.get("alert_id") or row.get("recommendation_id")
        if row.get("alert_id"):
            notification_type = "alert"
        elif row.get("recommendation_id"):
            notification_type = "recommendation"
        else:
            notification_type = "system"
        status = "read" if row.get("is_read") else "unread"
        connection.execute(
            """
            INSERT INTO notifications (
                notification_id,
                client_id,
                notification_type,
                reference_id,
                title,
                message,
                channel,
                status,
                created_at,
                read_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row.get("notification_id"),
                DEFAULT_CLIENT_ID,
                notification_type,
                reference_id,
                row.get("title", ""),
                row.get("body"),
                row.get("channel"),
                status,
                row.get("created_at"),
                row.get("read_at"),
            ),
        )

    connection.execute("DROP TABLE notifications_legacy")


def _migrate_recommendations_if_needed(connection: sqlite3.Connection) -> None:
    """Migre la table recommendations du schema Phase 1 vers le schema Wave 5.

    Si la table n'existe pas, la fonction n'intervient pas.
    Si la table possede deja trigger_type (schema Wave 5), aucune action.
    Sinon, renomme la table legacy, recree la table cible, migre les donnees,
    puis supprime la table temporaire.
    """
    if not _table_exists(connection, "recommendations"):
        return
    columns = _column_definitions(connection, "recommendations")
    if "trigger_type" in columns:
        return
    logger.info("Migration SQLite : realignement de la table recommendations vers schema Wave 5")
    connection.execute("ALTER TABLE recommendations RENAME TO recommendations_legacy")
    connection.execute(_SCHEMA_STATEMENTS["recommendations"])
    connection.execute(
        f"""
        INSERT INTO recommendations (
            recommendation_id,
            client_id,
            trigger_type,
            trigger_id,
            alert_id,
            analysis_summary,
            recommendations,
            watchlist_priorities,
            confidence_score,
            data_quality_note,
            provider_used,
            model_used,
            context_tokens,
            generation_ms,
            status,
            created_at
        )
        SELECT
            {_select_or_default(columns, "recommendation_id", "'rec-' || lower(hex(randomblob(6)))")},
            'ramy_client_001',
            'manual',
            NULL,
            {_select_or_default(columns, "alert_id", "NULL")},
            {_select_or_default(columns, "problem", "''")},
            CASE
                WHEN {_select_or_default(columns, "actions", "NULL")} IS NULL
                    OR {_select_or_default(columns, "actions", "NULL")} = ''
                THEN '[]'
                ELSE json_array({_select_or_default(columns, "actions", "NULL")})
            END,
            '[]',
            NULL,
            {_select_or_default(columns, "evidence_summary", "NULL")},
            {_select_or_default(columns, "generation_mode", "NULL")},
            NULL,
            NULL,
            NULL,
            'active',
            {_select_or_default(columns, "created_at", "CURRENT_TIMESTAMP")}
        FROM recommendations_legacy
        """
    )
    connection.execute("DROP TABLE recommendations_legacy")


def _seed_default_alert_rules(connection: sqlite3.Connection) -> None:
    """Insere les regles v1 si elles sont absentes."""
    defaults = [
        ("nss_critical_low", "NSS critique bas", "absolute", 20.0, "lt", "7d", "high"),
        ("negative_volume_surge", "Pic de volume negatif", "relative", 60.0, "gt", "7d", "high"),
        ("no_recent_signals", "Aucun signal recent", "drift", 7.0, "gte", "7d", "high"),
        ("aspect_critical", "Aspect critique", "absolute", -10.0, "lt", "7d", "high"),
        ("volume_drop", "Chute de volume", "relative", 50.0, "lt", "7d", "medium"),
        ("volume_anomaly", "Anomalie statistique de volume", "anomaly", 2.0, "gt", "8d", "high"),
        ("nss_temporal_drift", "Derive temporelle NSS", "drift", 3.0, "lt", "3d", "high"),
        ("segment_divergence", "Divergence entre segments", "divergence", 25.0, "gt", "7d", "high"),
        ("campaign_impact_positive", "Impact campagne positif", "relative", 10.0, "gt", "30d", "high"),
        ("campaign_underperformance", "Sous-performance campagne", "relative", 0.0, "lte", "7d", "medium"),
    ]
    for alert_rule_id, rule_name, rule_type, threshold_value, comparator, lookback_window, severity in defaults:
        connection.execute(
            """
            INSERT OR IGNORE INTO alert_rules (
                alert_rule_id,
                client_id,
                watchlist_id,
                rule_name,
                rule_type,
                threshold_value,
                comparator,
                lookback_window,
                severity_level,
                is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                alert_rule_id,
                DEFAULT_CLIENT_ID,
                None,
                rule_name,
                rule_type,
                threshold_value,
                comparator,
                lookback_window,
                severity,
                1,
            ),
        )


def _seed_default_client_agent_config(connection: sqlite3.Connection) -> None:
    """Insere une configuration agent par defaut pour le client mono-tenant."""
    connection.execute(
        """
        INSERT OR IGNORE INTO client_agent_config (
            config_id,
            client_id,
            provider,
            model,
            api_key_encrypted,
            auto_trigger_on_alert,
            auto_trigger_severity,
            weekly_report_enabled,
            weekly_report_day,
            created_at,
            updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """,
        (
            "cfg-default-agent",
            DEFAULT_CLIENT_ID,
            DEFAULT_AGENT_PROVIDER,
            DEFAULT_AGENT_MODEL,
            None,
            0,
            "critical",
            0,
            1,
        ),
    )


def _seed_default_client(connection: sqlite3.Connection) -> None:
    """Insere le client mono-tenant par defaut pour la couche plateforme."""
    connection.execute(
        """
        INSERT OR IGNORE INTO clients (
            client_id,
            client_name,
            industry,
            created_at,
            updated_at
        ) VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """,
        (
            DEFAULT_CLIENT_ID,
            "Ramy",
            "Agroalimentaire algerien",
        ),
    )


class DatabaseManager:
    """Gestionnaire de connexion SQLite pour RamyPulse."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        """Initialise la connexion SQLite et active les contraintes utiles."""
        resolved = SQLITE_DB_PATH if db_path is None else db_path
        self.db_path = str(resolved)
        self._conn: sqlite3.Connection | None = None

        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    @property
    def connection(self) -> sqlite3.Connection:
        """Expose une connexion SQLite active compatible avec les anciens tests."""
        return self.get_connection()

    def _connect(self) -> sqlite3.Connection:
        """Ouvre la connexion SQLite et prepare les pragmas requis."""
        connection = sqlite3.connect(self.db_path, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        if self.db_path != ":memory:":
            connection.execute("PRAGMA journal_mode=WAL")
        logger.debug("Connexion SQLite ouverte : %s", self.db_path)
        return connection

    def get_connection(self) -> sqlite3.Connection:
        """Retourne la connexion SQLite, en la creant si necessaire."""
        if self._conn is None:
            self._conn = self._connect()
        return self._conn

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        """Execute une requete SQL simple et retourne le curseur."""
        return self.get_connection().execute(sql, params)

    def executemany(self, sql: str, params_list: list[tuple]) -> sqlite3.Cursor:
        """Execute une requete SQL pour plusieurs jeux de parametres."""
        return self.get_connection().executemany(sql, params_list)

    def commit(self) -> None:
        """Valide la transaction courante."""
        if self._conn is not None:
            self._conn.commit()

    def create_tables(self) -> None:
        """Cree l'ensemble des tables SQLite du PRD et migre le legacy."""
        connection = self.get_connection()
        connection.execute("PRAGMA foreign_keys = OFF")
        try:
            _migrate_products_if_needed(connection)
            _migrate_wilayas_if_needed(connection)
            _migrate_competitors_if_needed(connection)
            _migrate_watchlists_if_needed(connection)
            _migrate_campaigns_if_needed(connection)
            _migrate_alerts_if_needed(connection)
            _migrate_notifications_if_needed(connection)
            _migrate_recommendations_if_needed(connection)

            for statement in _SCHEMA_STATEMENTS.values():
                connection.execute(statement)
            _seed_default_client(connection)
            _seed_default_alert_rules(connection)
            _seed_default_client_agent_config(connection)
            connection.commit()
        finally:
            connection.execute("PRAGMA foreign_keys = ON")

    def close(self) -> None:
        """Ferme proprement la connexion SQLite."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None
            logger.debug("Connexion SQLite fermee : %s", self.db_path)
