"""Page Streamlit de gestion des watchlists."""

from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

from config import ANNOTATED_PARQUET_PATH, DEFAULT_CLIENT_ID
from core.alerts.alert_detector import compute_watchlist_metrics
from core.runtime.diagnostics import collect_runtime_diagnostics
from core.watchlists.watchlist_manager import (
    create_watchlist,
    deactivate_watchlist,
    list_watchlists,
    suggest_watchlists,
)
from ui_helpers.annotated_data import load_annotated_parquet
from ui_helpers.runtime_panel import render_runtime_panel

logger = logging.getLogger(__name__)

st.set_page_config(page_title="Watchlists — RamyPulse", layout="wide")


@st.cache_data(ttl=300)
def load_data() -> pd.DataFrame:
    """Charge les donnees annotees ou retourne un DataFrame vide."""
    return load_annotated_parquet(ANNOTATED_PARQUET_PATH)


@st.cache_data(ttl=60, show_spinner=False)
def load_runtime_diagnostics() -> dict:
    """Charge le diagnostic runtime partage."""
    return collect_runtime_diagnostics()


def _options_from_column(dataframe: pd.DataFrame, column: str) -> list[str]:
    """Construit des options de selectbox a partir d'une colonne du DataFrame."""
    if column not in dataframe.columns:
        return []
    values = (
        dataframe[column]
        .dropna()
        .astype(str)
        .map(str.strip)
        .replace("", pd.NA)
        .dropna()
        .sort_values()
        .unique()
        .tolist()
    )
    return [str(value) for value in values]


def _select_or_none(label: str, options: list[str], key: str) -> str | None:
    """Affiche une selectbox avec une option Tous/Toutes."""
    values = ["Tous"] + options
    selected = st.selectbox(label, values, key=key)
    return None if selected == "Tous" else selected


def _create_watchlist_form(dataframe: pd.DataFrame) -> None:
    """Rend le formulaire de creation de watchlist."""
    with st.form("watchlist_form", clear_on_submit=True):
        st.subheader("Nouvelle watchlist")
        name = st.text_input("Nom de la watchlist")
        description = st.text_area("Description", height=80)
        scope_type = st.selectbox(
            "Type de scope",
            ["product", "region", "channel", "cross_dimension"],
        )

        filter_left, filter_right = st.columns(2)
        with filter_left:
            channel = _select_or_none("Canal", _options_from_column(dataframe, "channel"), "wl_channel")
            aspect = _select_or_none("Aspect", _options_from_column(dataframe, "aspect"), "wl_aspect")
            wilaya = _select_or_none("Wilaya", _options_from_column(dataframe, "wilaya"), "wl_wilaya")
        with filter_right:
            product = _select_or_none("Produit", _options_from_column(dataframe, "product"), "wl_product")
            sentiment = _select_or_none(
                "Sentiment",
                _options_from_column(dataframe, "sentiment_label"),
                "wl_sentiment",
            )
            period_days = int(st.number_input("Fenetre (jours)", min_value=1, value=7, step=1))
            min_volume = int(st.number_input("Volume minimum", min_value=0, value=10, step=1))

        submitted = st.form_submit_button("Creer la watchlist", use_container_width=True)
        if not submitted:
            return

        try:
            watchlist_id = create_watchlist(
                name=name,
                description=description,
                scope_type=scope_type,
                filters={
                    "channel": channel,
                    "aspect": aspect,
                    "wilaya": wilaya.lower() if wilaya else None,
                    "product": product.lower() if product else None,
                    "sentiment": sentiment,
                    "period_days": period_days,
                    "min_volume": min_volume,
                },
            )
        except (sqlite3.Error, RuntimeError, ValueError) as exc:
            logger.exception("Echec creation watchlist")
            st.error(f"Impossible de creer la watchlist: {exc}")
            return

        st.success(f"Watchlist creee: {watchlist_id}")
        st.rerun()


def _render_suggested_watchlists(dataframe: pd.DataFrame) -> None:
    """Affiche des watchlists suggerees automatiquement a partir des donnees courantes."""
    suggestions = suggest_watchlists(dataframe, limit=3)
    st.subheader("Watchlists suggerees")
    if not suggestions:
        st.info("Pas assez de signaux faibles pour suggerer de nouvelles watchlists automatiquement.")
        return

    for index, suggestion in enumerate(suggestions, start=1):
        header = (
            f"{suggestion['watchlist_name']} | NSS {suggestion['metrics']['nss']:.1f} | "
            f"volume {suggestion['metrics']['volume']}"
        )
        with st.expander(header, expanded=(index == 1)):
            st.write(suggestion["description"])
            st.caption(suggestion["reason"])
            st.json(suggestion["filters"])
            if st.button(
                "Creer cette watchlist",
                key=f"create_suggested_watchlist_{index}",
                use_container_width=True,
            ):
                try:
                    create_watchlist(
                        name=suggestion["watchlist_name"],
                        description=suggestion["description"],
                        scope_type=suggestion["scope_type"],
                        filters=suggestion["filters"],
                    )
                except (sqlite3.Error, RuntimeError, ValueError) as exc:
                    logger.exception("Echec creation watchlist suggeree")
                    st.error(f"Impossible de creer la watchlist suggeree: {exc}")
                else:
                    st.success("Watchlist suggeree creee.")
                    st.rerun()


def _metrics_dataframe(watchlists: list[dict], dataframe: pd.DataFrame) -> pd.DataFrame:
    """Construit le tableau synthetique des metriques de watchlists."""
    rows: list[dict[str, object]] = []
    for watchlist in watchlists:
        metrics = compute_watchlist_metrics(watchlist, dataframe)
        rows.append(
            {
                "watchlist_id": watchlist["watchlist_id"],
                "nom": watchlist["watchlist_name"],
                "scope_type": watchlist["scope_type"],
                "active": bool(watchlist["is_active"]),
                "nss_courant": metrics["nss_current"],
                "nss_precedent": metrics["nss_previous"],
                "delta_nss": metrics["delta_nss"],
                "volume_courant": metrics["volume_current"],
                "volume_precedent": metrics["volume_previous"],
                "filtres": json.dumps(watchlist["filters"], ensure_ascii=False),
            }
        )
    return pd.DataFrame(rows)


df = load_data()

st.title("🎯 Watchlists")
st.caption(f"Configuration des perimetres de surveillance pour le client {DEFAULT_CLIENT_ID}.")
render_runtime_panel(load_runtime_diagnostics(), title="Diagnostic runtime")

if df.empty:
    st.warning("⚠️ Données non disponibles. Lancez d'abord scripts/run_demo_05.py")
    st.stop()

try:
    watchlists = list_watchlists(is_active=False)
except (sqlite3.Error, RuntimeError, ValueError) as exc:
    logger.exception("Echec chargement watchlists")
    st.error(f"Impossible de charger les watchlists: {exc}")
    st.stop()

top_left, top_mid, top_right = st.columns(3)
top_left.metric("Watchlists totales", len(watchlists))
top_mid.metric("Watchlists actives", sum(1 for row in watchlists if row["is_active"]))
top_right.metric("Canaux disponibles", df["channel"].nunique() if "channel" in df.columns else 0)

st.divider()
layout_left, layout_right = st.columns([1, 2])

with layout_left:
    _create_watchlist_form(df)
    st.divider()
    _render_suggested_watchlists(df)

with layout_right:
    st.subheader("Watchlists configurees")
    if not watchlists:
        st.info("Aucune watchlist configuree pour le moment.")
    else:
        try:
            metrics_df = _metrics_dataframe(watchlists, df)
        except (sqlite3.Error, RuntimeError, ValueError) as exc:
            logger.exception("Echec calcul metriques watchlists")
            st.error(f"Impossible de calculer les metriques: {exc}")
        else:
            st.dataframe(metrics_df, use_container_width=True, hide_index=True)

        for watchlist in watchlists:
            with st.expander(f"{watchlist['watchlist_name']} — {watchlist['scope_type']}"):
                st.write(watchlist["description"] or "Sans description.")
                st.json(watchlist["filters"])
                action_columns = st.columns([1, 1, 2])
                with action_columns[0]:
                    st.caption("Active" if watchlist["is_active"] else "Inactive")
                with action_columns[1]:
                    if watchlist["is_active"] and st.button(
                        "Desactiver",
                        key=f"deactivate_{watchlist['watchlist_id']}",
                        use_container_width=True,
                    ):
                        try:
                            deactivate_watchlist(watchlist["watchlist_id"])
                        except (sqlite3.Error, RuntimeError, ValueError) as exc:
                            logger.exception("Echec desactivation watchlist")
                            st.error(f"Impossible de desactiver: {exc}")
                        else:
                            st.rerun()
                with action_columns[2]:
                    st.code(watchlist["watchlist_id"], language="text")

if Path(__file__).with_name("07_alerts.py").exists():
    st.page_link("pages/07_alerts.py", label="Ouvrir le centre d'alertes")
