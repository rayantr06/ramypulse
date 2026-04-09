"""Gestion CRUD des watchlists RamyPulse."""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from datetime import datetime

import config
import pandas as pd

logger = logging.getLogger(__name__)

_LEGACY_DEFAULT_FILTERS = {
    "channel": None,
    "aspect": None,
    "wilaya": None,
    "product": None,
    "sentiment": None,
    "period_days": 7,
    "min_volume": 10,
}
_WATCH_SEED_DEFAULT_FILTERS = {
    "brand_name": None,
    "product_name": None,
    "keywords": [],
    "seed_urls": [],
    "competitors": [],
    "channels": [],
    "languages": [],
    "hashtags": [],
    "period_days": 7,
    "min_volume": 10,
}
_WATCH_SEED_SEMANTIC_KEYS = {
    "brand_name",
    "product_name",
    "keywords",
    "seed_urls",
    "competitors",
    "channels",
    "languages",
    "hashtags",
}
_VALID_SCOPE_TYPES = {"product", "region", "channel", "cross_dimension", "watch_seed"}
_REQUIRED_COLUMNS = {
    "watchlist_id",
    "client_id",
    "watchlist_name",
    "description",
    "scope_type",
    "filters",
    "is_active",
    "created_at",
    "updated_at",
}


def _get_connection() -> sqlite3.Connection:
    """Retourne une connexion SQLite courte duree avec row_factory activee."""
    connection = sqlite3.connect(config.SQLITE_DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def _deserialize_dict(value: str | None) -> dict:
    """Deserialise une chaine JSON en dictionnaire Python."""
    if not value:
        return {}
    try:
        payload = json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _serialize_dict(value: dict | None) -> str:
    """Serialise un dictionnaire vers une chaine JSON SQLite."""
    return json.dumps(value or {}, ensure_ascii=False)


def _new_id() -> str:
    """Genere un identifiant UUID textuel."""
    return str(uuid.uuid4())


def _now() -> str:
    """Retourne un timestamp ISO courant."""
    return datetime.now().isoformat()


def _normalize_text(value: object) -> str | None:
    """Normalise une valeur texte simple pour stockage et comparaison."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_int(value: object, default: int) -> int:
    """Normalise un entier de filtre avec valeur de repli."""
    if value in (None, ""):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize_string_list(
    value: object,
    *,
    lowercase: bool = False,
) -> list[str]:
    """Normalise une liste de chaines en conservant l'ordre et l'unicite."""
    if value in (None, ""):
        return []

    if isinstance(value, (list, tuple, set)):
        raw_items = list(value)
    else:
        raw_items = [value]

    normalized: list[str] = []
    seen: set[str] = set()
    for item in raw_items:
        text = _normalize_text(item)
        if not text:
            continue
        candidate = text.lower() if lowercase else text
        if candidate in seen:
            continue
        seen.add(candidate)
        normalized.append(candidate)
    return normalized


def _uses_watch_seed_shape(filters: dict | None, scope_type: str | None = None) -> bool:
    """Determine si les filtres doivent utiliser le contrat watch_seed."""
    if scope_type == "watch_seed":
        return True
    if scope_type in _VALID_SCOPE_TYPES:
        return False
    if not filters:
        return False
    return any(key in _WATCH_SEED_SEMANTIC_KEYS for key in filters)


def _normalize_legacy_filters(filters: dict | None) -> dict:
    """Normalise les filtres legacy sans ajouter les cles watch_seed."""
    payload = dict(_LEGACY_DEFAULT_FILTERS)
    payload.update(filters or {})
    return {
        "channel": _normalize_text(payload.get("channel")),
        "aspect": _normalize_text(payload.get("aspect")),
        "wilaya": _normalize_text(payload.get("wilaya")),
        "product": _normalize_text(payload.get("product")),
        "sentiment": _normalize_text(payload.get("sentiment")),
        "period_days": max(1, _normalize_int(payload.get("period_days"), 7)),
        "min_volume": max(0, _normalize_int(payload.get("min_volume"), 10)),
    }


def _normalize_watch_seed_filters(filters: dict | None) -> dict:
    """Normalise les filtres watch_seed en preservant uniquement ce contrat."""
    payload = dict(_WATCH_SEED_DEFAULT_FILTERS)
    payload.update(filters or {})
    return {
        "brand_name": _normalize_text(payload.get("brand_name")),
        "product_name": _normalize_text(payload.get("product_name")),
        "keywords": _normalize_string_list(payload.get("keywords"), lowercase=True),
        "seed_urls": _normalize_string_list(payload.get("seed_urls")),
        "competitors": _normalize_string_list(payload.get("competitors")),
        "channels": _normalize_string_list(payload.get("channels"), lowercase=True),
        "languages": _normalize_string_list(payload.get("languages"), lowercase=True),
        "hashtags": _normalize_string_list(payload.get("hashtags"), lowercase=True),
        "period_days": max(1, _normalize_int(payload.get("period_days"), 7)),
        "min_volume": max(0, _normalize_int(payload.get("min_volume"), 10)),
    }


def _normalize_filters(filters: dict | None, *, scope_type: str | None = None) -> dict:
    """Valide et complete la structure de filtres contractuelle."""
    if _uses_watch_seed_shape(filters, scope_type):
        return _normalize_watch_seed_filters(filters)
    return _normalize_legacy_filters(filters)


def _validate_watch_seed_filters(filters: dict) -> None:
    """Refuse les watchlists watch_seed sans seed semantique exploitable."""
    meaningful_seed = any(
        (
            filters.get("brand_name"),
            filters.get("product_name"),
            filters.get("keywords"),
            filters.get("seed_urls"),
            filters.get("competitors"),
            filters.get("hashtags"),
        )
    )
    if not meaningful_seed:
        raise ValueError("watch_seed requires at least one meaningful seed")


def _validate_scope_type(scope_type: str) -> str:
    """Valide le type de perimetre de watchlist."""
    if scope_type not in _VALID_SCOPE_TYPES:
        raise ValueError(f"scope_type invalide: {scope_type}")
    return scope_type


def _table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
    """Indique si une table SQLite existe deja."""
    row = connection.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table' AND name = ?
        """,
        (table_name,),
    ).fetchone()
    return row is not None


def _table_columns(connection: sqlite3.Connection, table_name: str) -> set[str]:
    """Liste les colonnes disponibles pour une table SQLite."""
    rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row["name"] for row in rows}


def _ensure_watchlists_table(connection: sqlite3.Connection) -> None:
    """Garantit la presence de la table watchlists conforme au contrat."""
    if _table_exists(connection, "watchlists"):
        columns = _table_columns(connection, "watchlists")
        missing = _REQUIRED_COLUMNS - columns
        if missing:
            raise RuntimeError(
                "Schema watchlists incompatible avec INTERFACES.md: "
                f"colonnes manquantes {sorted(missing)}"
            )
        return

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS watchlists (
            watchlist_id TEXT PRIMARY KEY,
            client_id TEXT DEFAULT 'ramy_client_001',
            watchlist_name TEXT NOT NULL,
            description TEXT,
            scope_type TEXT,
            filters TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TEXT,
            updated_at TEXT
        )
        """
    )
    connection.commit()


def _row_to_watchlist(row: sqlite3.Row | None) -> dict | None:
    """Convertit une ligne SQLite en dictionnaire de watchlist."""
    if row is None:
        return None
    payload = dict(row)
    payload["filters"] = _normalize_filters(
        _deserialize_dict(payload.get("filters")),
        scope_type=payload.get("scope_type"),
    )
    payload["is_active"] = int(payload.get("is_active", 0))
    return payload


def create_watchlist(
    name: str,
    description: str,
    scope_type: str,
    filters: dict,
) -> str:
    """Cree une watchlist et retourne son identifiant."""
    if not name or not str(name).strip():
        raise ValueError("name est requis")

    normalized_scope_type = _validate_scope_type(scope_type)
    normalized_filters = _normalize_filters(filters, scope_type=normalized_scope_type)
    if normalized_scope_type == "watch_seed":
        _validate_watch_seed_filters(normalized_filters)
    watchlist_id = _new_id()
    timestamp = _now()

    with _get_connection() as connection:
        _ensure_watchlists_table(connection)
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
                watchlist_id,
                config.DEFAULT_CLIENT_ID,
                str(name).strip(),
                description.strip() if description else "",
                normalized_scope_type,
                _serialize_dict(normalized_filters),
                1,
                timestamp,
                timestamp,
            ),
        )
        connection.commit()

    logger.info("Watchlist creee: %s", watchlist_id)
    return watchlist_id


def list_watchlists(is_active: bool = True) -> list[dict]:
    """Liste les watchlists avec filtres deserialises automatiquement."""
    with _get_connection() as connection:
        _ensure_watchlists_table(connection)
        sql = "SELECT * FROM watchlists"
        params: list[object] = []
        if is_active:
            sql += " WHERE is_active = 1"
        sql += " ORDER BY created_at DESC, watchlist_id DESC"
        rows = connection.execute(sql, params).fetchall()

    return [_row_to_watchlist(row) for row in rows]


def get_watchlist(watchlist_id: str) -> dict | None:
    """Retourne une watchlist complete ou None si absente."""
    with _get_connection() as connection:
        _ensure_watchlists_table(connection)
        row = connection.execute(
            "SELECT * FROM watchlists WHERE watchlist_id = ?",
            (watchlist_id,),
        ).fetchone()
    return _row_to_watchlist(row)


def update_watchlist(watchlist_id: str, updates: dict) -> bool:
    """Met a jour une watchlist avec un sous-ensemble arbitraire de champs."""
    current = get_watchlist(watchlist_id)
    if current is None:
        return False

    if not updates:
        return True

    allowed = {
        "client_id",
        "watchlist_name",
        "description",
        "scope_type",
        "filters",
        "is_active",
    }
    payload = {key: value for key, value in dict(updates).items() if key in allowed}
    if not payload:
        return True

    if "watchlist_name" in payload:
        name = str(payload["watchlist_name"]).strip()
        if not name:
            raise ValueError("watchlist_name est requis")
        payload["watchlist_name"] = name

    if "scope_type" in payload:
        payload["scope_type"] = _validate_scope_type(str(payload["scope_type"]))

    effective_scope_type = str(payload.get("scope_type") or current["scope_type"])

    if "filters" in payload:
        merged_filters = _normalize_filters(
            current.get("filters"),
            scope_type=effective_scope_type,
        )
        merged_filters.update(dict(payload["filters"] or {}))
        normalized_filters = _normalize_filters(
            merged_filters,
            scope_type=effective_scope_type,
        )
        if effective_scope_type == "watch_seed":
            _validate_watch_seed_filters(normalized_filters)
        payload["filters"] = _serialize_dict(normalized_filters)
    elif "scope_type" in payload:
        normalized_filters = _normalize_filters(
            current.get("filters"),
            scope_type=effective_scope_type,
        )
        if effective_scope_type == "watch_seed":
            _validate_watch_seed_filters(normalized_filters)
        payload["filters"] = _serialize_dict(normalized_filters)

    if "description" in payload:
        payload["description"] = str(payload["description"] or "").strip()

    if "is_active" in payload:
        payload["is_active"] = 1 if bool(payload["is_active"]) else 0

    payload["updated_at"] = _now()
    assignments = ", ".join(f"{column} = ?" for column in payload)
    params = list(payload.values()) + [watchlist_id]

    with _get_connection() as connection:
        _ensure_watchlists_table(connection)
        cursor = connection.execute(
            f"UPDATE watchlists SET {assignments} WHERE watchlist_id = ?",
            params,
        )
        connection.commit()

    updated = cursor.rowcount > 0
    if updated:
        logger.info("Watchlist mise a jour: %s", watchlist_id)
    return updated


def deactivate_watchlist(watchlist_id: str) -> bool:
    """Desactive une watchlist sans la supprimer."""
    return update_watchlist(watchlist_id, {"is_active": 0})


def suggest_watchlists(df_annotated: pd.DataFrame, limit: int = 5) -> list[dict]:
    """Propose des watchlists automatiques a partir des segments les plus fragiles.

    Heuristique v1:
    - groupe par couple wilaya x aspect
    - retient les segments avec au moins 3 signaux
    - trie par NSS croissant puis volume decroissant
    """
    if df_annotated.empty:
        return []

    dataframe = df_annotated.copy()
    for column in ("aspect", "wilaya", "channel", "product", "sentiment_label"):
        if column not in dataframe.columns:
            dataframe[column] = None
    dataframe["aspect"] = dataframe["aspect"].fillna("").astype(str).str.strip()
    dataframe["wilaya"] = dataframe["wilaya"].fillna("").astype(str).str.strip().str.lower()
    dataframe["channel"] = dataframe["channel"].fillna("").astype(str).str.strip().str.lower()
    dataframe["product"] = dataframe["product"].fillna("").astype(str).str.strip().str.lower()

    candidates: list[dict] = []
    grouped = dataframe.groupby(["wilaya", "aspect"], dropna=False)
    for (wilaya, aspect), group in grouped:
        if not wilaya or not aspect or len(group) < 3:
            continue

        positives = int(group["sentiment_label"].isin({"très_positif", "positif"}).sum())
        negatives = int(group["sentiment_label"].isin({"très_négatif", "négatif"}).sum())
        nss = round(((positives - negatives) / len(group)) * 100.0, 2)
        channel_mode = (
            group["channel"].mode(dropna=True).iloc[0]
            if not group["channel"].dropna().empty
            else None
        )
        product_mode = (
            group["product"].mode(dropna=True).iloc[0]
            if not group["product"].dropna().empty
            else None
        )

        candidates.append(
            {
                "watchlist_name": f"Surveillance {aspect} {wilaya.title()}",
                "description": (
                    f"Suggestion auto pour surveiller {aspect} sur {wilaya.title()} "
                    f"apres un NSS de {nss:.1f} sur {len(group)} signaux."
                ),
                "scope_type": "cross_dimension",
                "filters": _normalize_filters(
                    {
                        "channel": channel_mode or None,
                        "aspect": aspect,
                        "wilaya": wilaya,
                        "product": product_mode or None,
                        "sentiment": None,
                        "period_days": 7,
                        "min_volume": max(3, min(10, len(group))),
                    }
                ),
                "reason": f"NSS {aspect}/{wilaya} = {nss:.1f} sur {len(group)} signaux.",
                "metrics": {
                    "nss": nss,
                    "volume": int(len(group)),
                    "positive_count": positives,
                    "negative_count": negatives,
                },
            }
        )

    candidates.sort(
        key=lambda item: (
            float(item["metrics"]["nss"]),
            -int(item["metrics"]["volume"]),
            item["watchlist_name"],
        )
    )
    return candidates[: max(0, limit)]
