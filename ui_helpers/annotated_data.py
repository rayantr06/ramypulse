"""Helpers de chargement et normalisation des datasets annotes pour l'UI."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pandas as pd


def _coerce_sequence(value: object) -> list[object]:
    """Convertit une cellule potentiellement serialisee en liste Python."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return []
        for parser in (json.loads, ast.literal_eval):
            try:
                parsed = parser(stripped)
            except Exception:
                continue
            if isinstance(parsed, list):
                return parsed
        return [stripped]
    return [value]


def _extract_primary_aspect(row: pd.Series) -> str:
    """Extrait l'aspect principal d'une ligne a partir des colonnes disponibles."""
    aspect = row.get("aspect")
    if pd.notna(aspect) and str(aspect).strip():
        return str(aspect).strip()

    for item in _coerce_sequence(row.get("aspects")):
        if item is None:
            continue
        text = str(item).strip()
        if text:
            return text

    for item in _coerce_sequence(row.get("aspect_sentiments")):
        if isinstance(item, dict):
            candidate = item.get("aspect")
            if candidate is not None and str(candidate).strip():
                return str(candidate).strip()
        elif item is not None and str(item).strip():
            return str(item).strip()

    return ""


def normalize_annotated_dataframe(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Normalise un DataFrame annote pour les pages Streamlit."""
    normalized = dataframe.copy()

    if "timestamp" in normalized.columns:
        normalized["timestamp"] = pd.to_datetime(normalized["timestamp"], errors="coerce")

    if normalized.empty:
        normalized["aspect"] = pd.Series(dtype="object")
    else:
        normalized["aspect"] = normalized.apply(_extract_primary_aspect, axis=1)
    normalized["aspect"] = normalized["aspect"].fillna("").astype(str)

    if "wilaya" in normalized.columns:
        normalized["wilaya"] = normalized["wilaya"].fillna("").astype(str).str.lower().str.strip()

    return normalized


def load_annotated_parquet(path: Path | str) -> pd.DataFrame:
    """Charge un parquet annote depuis le disque et applique la normalisation UI."""
    file_path = Path(path)
    if not file_path.exists():
        return pd.DataFrame()
    return normalize_annotated_dataframe(pd.read_parquet(file_path))
