"""Helpers purs pour les pages d'administration Phase 1."""

from __future__ import annotations

import pandas as pd


_SOURCE_COLUMNS = [
    "source_id",
    "display_name",
    "platform",
    "owner_type",
    "source_type",
    "brand",
    "is_active",
    "last_sync_at",
]


def filter_source_records(
    records: list[dict],
    platform: str | None = None,
    owner_type: str | None = None,
    status: str = "all",
) -> list[dict]:
    """Filtre des sources deja chargees en memoire."""
    filtered = list(records)

    if platform and platform != "all":
        filtered = [row for row in filtered if row.get("platform") == platform]

    if owner_type and owner_type != "all":
        filtered = [row for row in filtered if row.get("owner_type") == owner_type]

    if status == "active":
        filtered = [row for row in filtered if bool(row.get("is_active"))]
    elif status == "inactive":
        filtered = [row for row in filtered if not bool(row.get("is_active"))]

    return filtered


def build_sources_frame(records: list[dict]) -> pd.DataFrame:
    """Construit un DataFrame stable pour l'affichage admin sources."""
    frame = pd.DataFrame(records)
    for column in _SOURCE_COLUMNS:
        if column not in frame.columns:
            frame[column] = []
    if frame.empty:
        return pd.DataFrame(columns=_SOURCE_COLUMNS)
    return frame[_SOURCE_COLUMNS].sort_values(
        by=["is_active", "display_name"],
        ascending=[False, True],
        na_position="last",
    )


def compute_source_metrics(records: list[dict]) -> dict[str, int]:
    """Calcule un resume simple pour la page admin sources."""
    total = len(records)
    active = sum(1 for row in records if bool(row.get("is_active")))
    platforms = len({row.get("platform") for row in records if row.get("platform")})
    return {
        "total": total,
        "active": active,
        "inactive": total - active,
        "platforms": platforms,
    }


def parse_keywords(raw: str) -> list[str]:
    """Transforme une saisie CSV simple en liste nettoyee."""
    return [part.strip() for part in raw.split(",") if part.strip()]


def build_catalog_frame(
    records: list[dict],
    preferred_columns: list[str],
) -> pd.DataFrame:
    """Construit un tableau catalogue avec un ordre de colonnes stable."""
    if not records:
        return pd.DataFrame(columns=preferred_columns)

    frame = pd.DataFrame(records)
    ordered_columns = [column for column in preferred_columns if column in frame.columns]
    missing_columns = [column for column in preferred_columns if column not in frame.columns]
    for column in missing_columns:
        frame[column] = None
    return frame[preferred_columns]


def compute_catalog_metrics(
    products: list[dict],
    wilayas: list[dict],
    competitors: list[dict],
) -> dict[str, int]:
    """Retourne les compteurs globaux du catalogue metier."""
    return {
        "products": len(products),
        "wilayas": len(wilayas),
        "competitors": len(competitors),
    }
