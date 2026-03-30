"""CRUD du registre de sources RamyPulse."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from core.database import DatabaseManager


_VALID_PLATFORMS = {
    "facebook",
    "instagram",
    "google_maps",
    "youtube",
    "sav",
    "import",
}

_VALID_OWNER_TYPES = {
    "owned",
    "competitor",
    "market",
}


class SourceRegistry:
    """Registre SQLite des sources surveillées par RamyPulse."""

    def __init__(self, database: DatabaseManager) -> None:
        """Initialise le registre sur une base déjà connectée."""
        self.database = database

    def create_source(self, payload: dict) -> dict:
        """Crée une source après validation des champs métier critiques."""
        data = dict(payload)
        data["source_id"] = data.get("source_id") or str(uuid.uuid4())
        data.setdefault("is_active", 1)
        data["updated_at"] = self._now()
        self._validate(data)

        columns = list(data.keys())
        placeholders = ", ".join("?" for _ in columns)
        sql = f"""
            INSERT INTO source_registry ({", ".join(columns)})
            VALUES ({placeholders})
        """
        self.database.connection.execute(sql, [data[col] for col in columns])
        self.database.connection.commit()
        return self.get_source(data["source_id"])

    def get_source(self, source_id: str) -> dict | None:
        """Retourne une source par identifiant, ou None si absente."""
        row = self.database.connection.execute(
            "SELECT * FROM source_registry WHERE source_id = ?",
            (source_id,),
        ).fetchone()
        return dict(row) if row is not None else None

    def list_sources(
        self,
        active_only: bool = False,
        platform: str | None = None,
        owner_type: str | None = None,
    ) -> list[dict]:
        """Liste les sources avec filtres optionnels."""
        clauses = []
        params: list[object] = []
        if active_only:
            clauses.append("is_active = 1")
        if platform is not None:
            clauses.append("platform = ?")
            params.append(platform)
        if owner_type is not None:
            clauses.append("owner_type = ?")
            params.append(owner_type)

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.database.connection.execute(
            f"SELECT * FROM source_registry {where} ORDER BY created_at, source_id",
            params,
        ).fetchall()
        return [dict(row) for row in rows]

    def update_source(self, source_id: str, updates: dict) -> dict:
        """Met à jour les champs fournis d'une source existante."""
        if not updates:
            current = self.get_source(source_id)
            if current is None:
                raise KeyError(source_id)
            return current

        current = self.get_source(source_id)
        if current is None:
            raise KeyError(source_id)

        data = dict(updates)
        data["updated_at"] = self._now()
        self._validate(data, partial=True)

        assignments = ", ".join(f"{column} = ?" for column in data.keys())
        params = [data[column] for column in data.keys()]
        params.append(source_id)
        self.database.connection.execute(
            f"UPDATE source_registry SET {assignments} WHERE source_id = ?",
            params,
        )
        self.database.connection.commit()
        return self.get_source(source_id)

    def mark_sync(self, source_id: str, synced_at: str | None = None) -> dict:
        """Met à jour l'horodatage de dernière synchronisation."""
        timestamp = synced_at or self._now()
        return self.update_source(
            source_id,
            {"last_sync_at": timestamp},
        )

    def deactivate_source(self, source_id: str) -> dict:
        """Désactive une source sans supprimer son historique."""
        return self.update_source(source_id, {"is_active": 0})

    def reactivate_source(self, source_id: str) -> dict:
        """Réactive une source précédemment désactivée."""
        return self.update_source(source_id, {"is_active": 1})

    def delete_source(self, source_id: str) -> None:
        """Supprime une source du registre."""
        self.database.connection.execute(
            "DELETE FROM source_registry WHERE source_id = ?",
            (source_id,),
        )
        self.database.connection.commit()

    def _validate(self, data: dict, partial: bool = False) -> None:
        """Valide les champs métier critiques du registre."""
        required = {"platform", "source_type", "display_name", "owner_type"}
        if not partial:
            missing = [field for field in required if not data.get(field)]
            if missing:
                raise ValueError(f"Champs requis manquants : {missing}")

        if "platform" in data and data["platform"] not in _VALID_PLATFORMS:
            raise ValueError(f"platform invalide : {data['platform']}")
        if "owner_type" in data and data["owner_type"] not in _VALID_OWNER_TYPES:
            raise ValueError(f"owner_type invalide : {data['owner_type']}")

    def _now(self) -> str:
        """Retourne un horodatage UTC ISO 8601."""
        return datetime.now(timezone.utc).isoformat()

