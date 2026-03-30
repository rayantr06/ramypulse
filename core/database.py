"""Infrastructure SQLite locale pour les objets metier RamyPulse.

Expose un gestionnaire unique compatible avec les besoins de l'infrastructure
Phase 1 et des catalogues metier.
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

from config import SQLITE_DB_PATH

logger = logging.getLogger(__name__)


_SCHEMA_STATEMENTS = {
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
    """,
    "campaigns": """
        CREATE TABLE IF NOT EXISTS campaigns (
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
    """,
    "alerts": """
        CREATE TABLE IF NOT EXISTS alerts (
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
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (watchlist_id) REFERENCES watchlists(watchlist_id)
        )
    """,
    "recommendations": """
        CREATE TABLE IF NOT EXISTS recommendations (
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

            for statement in _SCHEMA_STATEMENTS.values():
                connection.execute(statement)
            connection.commit()
        finally:
            connection.execute("PRAGMA foreign_keys = ON")

    def close(self) -> None:
        """Ferme proprement la connexion SQLite."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None
            logger.debug("Connexion SQLite fermee : %s", self.db_path)
