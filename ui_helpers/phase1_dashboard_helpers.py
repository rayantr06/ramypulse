"""Helpers purs pour les filtres Phase 1 du dashboard et de l'explorer."""

from __future__ import annotations

from datetime import date

import pandas as pd


_DEFAULT_EXPLORER_COLUMNS = [
    "text",
    "sentiment_label",
    "aspect",
    "channel",
    "product",
    "wilaya",
    "timestamp",
]


def build_available_filters(
    df: pd.DataFrame,
    columns: list[str],
) -> dict[str, list[str]]:
    """Construit les options disponibles pour chaque filtre demande."""
    options: dict[str, list[str]] = {}
    for column in columns:
        if column not in df.columns:
            options[column] = []
            continue
        values = df[column].dropna().astype(str).map(str.strip)
        values = values[values != ""]
        options[column] = sorted(values.unique().tolist(), key=str.casefold)
    return options


def missing_filter_columns(df: pd.DataFrame, columns: list[str]) -> list[str]:
    """Retourne les colonnes de filtre absentes du DataFrame."""
    return [column for column in columns if column not in df.columns]


def apply_dataframe_filters(
    df: pd.DataFrame,
    selected_filters: dict[str, object],
) -> pd.DataFrame:
    """Applique des filtres de facon defensive sur un DataFrame annote."""
    filtered = df.copy()

    date_range = selected_filters.get("date_range")
    if isinstance(date_range, tuple) and len(date_range) == 2 and "timestamp" in filtered.columns:
        timestamps = pd.to_datetime(filtered["timestamp"], errors="coerce")
        start = pd.Timestamp(date_range[0])
        end = pd.Timestamp(date_range[1]) + pd.Timedelta(days=1)
        filtered = filtered[(timestamps >= start) & (timestamps < end)]

    for column in ["channel", "aspect", "sentiment_label", "product", "wilaya"]:
        selected_values = selected_filters.get(column)
        if not selected_values or column not in filtered.columns:
            continue
        filtered = filtered[filtered[column].isin(selected_values)]

    return filtered


def build_explorer_display_columns(df: pd.DataFrame) -> list[str]:
    """Construit la liste ordonnee des colonnes visibles dans l'explorer."""
    return [column for column in _DEFAULT_EXPLORER_COLUMNS if column in df.columns]


def format_missing_dimensions(columns: list[str]) -> str:
    """Construit un message concis pour les dimensions metier absentes."""
    if not columns:
        return ""
    joined = ", ".join(columns)
    return (
        "Colonnes metier indisponibles pour le moment : "
        f"{joined}. Les pages restent exploitables en mode degrade."
    )


def default_date_range(df: pd.DataFrame) -> tuple[date, date]:
    """Retourne une plage de dates robuste pour les widgets Streamlit."""
    if not df.empty and "timestamp" in df.columns:
        timestamps = pd.to_datetime(df["timestamp"], errors="coerce").dropna()
        if not timestamps.empty:
            return timestamps.min().date(), timestamps.max().date()
    today = pd.Timestamp.today().date()
    return today, today
