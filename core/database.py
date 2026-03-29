"""Infrastructure SQLite locale pour les objets métier RamyPulse."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from config import SQLITE_DB_PATH


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
        product_id TEXT PRIMARY KEY,
        brand TEXT NOT NULL,
        product_line TEXT,
        product_name TEXT NOT NULL,
        sku TEXT,
        category TEXT,
        keywords_ar TEXT,
        keywords_arabizi TEXT,
        keywords_fr TEXT,
        is_active BOOLEAN DEFAULT TRUE,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS wilayas (
        wilaya_code TEXT PRIMARY KEY,
        wilaya_name_fr TEXT NOT NULL,
        wilaya_name_ar TEXT NOT NULL,
        keywords_arabizi TEXT,
        region TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS competitors (
        competitor_id TEXT PRIMARY KEY,
        brand_name TEXT NOT NULL,
        category TEXT,
        keywords_ar TEXT,
        keywords_arabizi TEXT,
        keywords_fr TEXT,
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
        self.connection = self._connect()

    def _connect(self) -> sqlite3.Connection:
        """Ouvre la connexion SQLite et prépare les pragmas requis."""
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def create_tables(self) -> None:
        """Crée l'ensemble des tables SQLite du PRD si elles n'existent pas."""
        cursor = self.connection.cursor()
        for statement in _SCHEMA_STATEMENTS:
            cursor.execute(statement)
        self.connection.commit()

    def close(self) -> None:
        """Ferme proprement la connexion SQLite."""
        self.connection.close()

