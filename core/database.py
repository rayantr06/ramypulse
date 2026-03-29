"""Infrastructure SQLite locale pour les objets métier RamyPulse.

Expose un gestionnaire unique compatible avec les besoins de l'infrastructure
Phase 1 et des catalogues métier.
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

from config import SQLITE_DB_PATH

logger = logging.getLogger(__name__)


_SCHEMA_STATEMENTS = [
    """
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
    """
    CREATE TABLE IF NOT EXISTS products (
        product_id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    """
    CREATE TABLE IF NOT EXISTS wilayas (
        wilaya_code TEXT PRIMARY KEY,
        name_fr TEXT NOT NULL,
        name_ar TEXT NOT NULL DEFAULT '',
        keywords_arabizi TEXT NOT NULL DEFAULT '[]',
        region TEXT NOT NULL DEFAULT ''
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS competitors (
        competitor_id INTEGER PRIMARY KEY AUTOINCREMENT,
        brand_name TEXT NOT NULL UNIQUE,
        category TEXT NOT NULL DEFAULT '',
        keywords_ar TEXT NOT NULL DEFAULT '[]',
        keywords_arabizi TEXT NOT NULL DEFAULT '[]',
        keywords_fr TEXT NOT NULL DEFAULT '[]',
        is_active BOOLEAN DEFAULT TRUE,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
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
    """
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
    """
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
    """
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
    """
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
    """
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
    """
    CREATE TABLE IF NOT EXISTS audit_log (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_type TEXT NOT NULL,
        source TEXT,
        details TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """,
]


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
        """Ouvre la connexion SQLite et prépare les pragmas requis."""
        connection = sqlite3.connect(self.db_path, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        if self.db_path != ":memory:":
            connection.execute("PRAGMA journal_mode=WAL")
        logger.debug("Connexion SQLite ouverte : %s", self.db_path)
        return connection

    def get_connection(self) -> sqlite3.Connection:
        """Retourne la connexion SQLite, en la créant si nécessaire."""
        if self._conn is None:
            self._conn = self._connect()
        return self._conn

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        """Exécute une requête SQL simple et retourne le curseur."""
        return self.get_connection().execute(sql, params)

    def executemany(self, sql: str, params_list: list[tuple]) -> sqlite3.Cursor:
        """Exécute une requête SQL pour plusieurs jeux de paramètres."""
        return self.get_connection().executemany(sql, params_list)

    def commit(self) -> None:
        """Valide la transaction courante."""
        if self._conn is not None:
            self._conn.commit()

    def create_tables(self) -> None:
        """Crée l'ensemble des tables SQLite du PRD si elles n'existent pas."""
        cursor = self.get_connection().cursor()
        for statement in _SCHEMA_STATEMENTS:
            cursor.execute(statement)
        self.get_connection().commit()

    def close(self) -> None:
        """Ferme proprement la connexion SQLite."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None
            logger.debug("Connexion SQLite fermée : %s", self.db_path)
