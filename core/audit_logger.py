"""Journal d'audit SQLite pour les événements métier RamyPulse."""

from __future__ import annotations

import json

from core.database import DatabaseManager


class AuditLogger:
    """Écrit et relit les événements d'audit métier."""

    def __init__(self, database: DatabaseManager) -> None:
        """Initialise le logger sur une base SQLite active."""
        self.database = database

    def log_event(
        self,
        event_type: str,
        source: str | None = None,
        details: dict | None = None,
    ) -> int:
        """Insère un événement dans la table audit_log."""
        payload = json.dumps(details or {}, ensure_ascii=False)
        cursor = self.database.connection.execute(
            """
            INSERT INTO audit_log (event_type, source, details)
            VALUES (?, ?, ?)
            """,
            (event_type, source, payload),
        )
        self.database.connection.commit()
        return int(cursor.lastrowid)

    def list_events(
        self,
        limit: int | None = None,
        event_type: str | None = None,
    ) -> list[dict]:
        """Retourne les événements d'audit, éventuellement filtrés."""
        clauses = []
        params: list[object] = []
        if event_type is not None:
            clauses.append("event_type = ?")
            params.append(event_type)

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        limit_clause = ""
        if limit is not None:
            limit_clause = " LIMIT ?"
            params.append(limit)

        rows = self.database.connection.execute(
            f"""
            SELECT * FROM audit_log
            {where}
            ORDER BY log_id DESC
            {limit_clause}
            """,
            params,
        ).fetchall()

        result = []
        for row in rows:
            item = dict(row)
            item["details"] = json.loads(item["details"]) if item["details"] else {}
            result.append(item)
        return result
