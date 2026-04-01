"""Centre d'alertes Streamlit pour RamyPulse."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

from config import ANNOTATED_PARQUET_PATH, DEFAULT_CLIENT_ID
from core.alerts.alert_detector import run_alert_detection
from core.alerts.alert_manager import list_alerts, update_alert_status

logger = logging.getLogger(__name__)

st.set_page_config(page_title="Alertes — RamyPulse", layout="wide")


@st.cache_data(ttl=300)
def load_data() -> pd.DataFrame:
    """Charge les donnees annotees ou retourne un DataFrame vide."""
    try:
        dataframe = pd.read_parquet(ANNOTATED_PARQUET_PATH)
        dataframe["timestamp"] = pd.to_datetime(dataframe["timestamp"], errors="coerce")
        return dataframe
    except FileNotFoundError:
        return pd.DataFrame()


def _status_options() -> list[str]:
    """Retourne la liste des statuts disponibles dans l'UI."""
    return ["Tous", "new", "acknowledged", "investigating", "resolved", "dismissed"]


def _severity_options() -> list[str]:
    """Retourne la liste des severites disponibles dans l'UI."""
    return ["Toutes", "critical", "high", "medium", "low"]


def _load_alerts(selected_status: str, selected_severity: str) -> list[dict]:
    """Charge les alertes selon les filtres actifs."""
    status = None if selected_status == "Tous" else selected_status
    severity = None if selected_severity == "Toutes" else selected_severity
    return list_alerts(status=status, severity=severity, limit=200)


def _status_button(label: str, status: str, alert_id: str, disabled: bool = False) -> None:
    """Affiche un bouton de transition de statut."""
    if st.button(label, key=f"{status}_{alert_id}", disabled=disabled, use_container_width=True):
        try:
            update_alert_status(alert_id, status)
        except (sqlite3.Error, RuntimeError, ValueError) as exc:
            logger.exception("Echec transition alerte")
            st.error(f"Impossible de mettre a jour l'alerte: {exc}")
        else:
            st.rerun()


df = load_data()

st.title("🚨 Centre d'alertes")
st.caption(f"Cycle de vie des alertes pour le client {DEFAULT_CLIENT_ID}.")

if df.empty:
    st.warning("⚠️ Données non disponibles. Lancez d'abord scripts/run_demo_05.py")
    st.stop()

toolbar_left, toolbar_right = st.columns([1, 2])
with toolbar_left:
    if st.button("Lancer une detection", type="primary", use_container_width=True):
        try:
            created_ids = run_alert_detection(df)
        except (sqlite3.Error, RuntimeError, ValueError) as exc:
            logger.exception("Echec detection alertes")
            st.error(f"Impossible de lancer la detection: {exc}")
        else:
            st.success(f"Cycle termine: {len(created_ids)} nouvelle(s) alerte(s).")
            st.rerun()
with toolbar_right:
    filter_columns = st.columns(2)
    selected_status = filter_columns[0].selectbox("Statut", _status_options())
    selected_severity = filter_columns[1].selectbox("Severite", _severity_options())

try:
    alerts = _load_alerts(selected_status, selected_severity)
except (sqlite3.Error, RuntimeError, ValueError) as exc:
    logger.exception("Echec chargement alertes")
    st.error(f"Impossible de charger les alertes: {exc}")
    st.stop()

summary = st.columns(4)
summary[0].metric("Alertes visibles", len(alerts))
summary[1].metric("Nouvelles", sum(1 for alert in alerts if alert["status"] == "new"))
summary[2].metric(
    "Critiques/hautes",
    sum(1 for alert in alerts if alert["severity"] in {"critical", "high"}),
)
summary[3].metric(
    "Resolues",
    sum(1 for alert in alerts if alert["status"] == "resolved"),
)

st.divider()

if not alerts:
    st.info("Aucune alerte pour les filtres selectionnes.")

for alert in alerts:
    title = f"[{alert['severity'].upper()}] {alert['title']} — {alert['status']}"
    with st.expander(title):
        st.write(alert["description"] or "Sans description detaillee.")
        meta_left, meta_mid, meta_right = st.columns(3)
        meta_left.caption(f"Detectee le {alert['detected_at']}")
        meta_mid.caption(f"Watchlist: {alert['watchlist_id'] or 'n/a'}")
        meta_right.caption(f"Regle: {alert['alert_rule_id'] or 'n/a'}")

        if alert.get("navigation_url"):
            st.code(alert["navigation_url"], language="text")

        payload = alert.get("alert_payload") or {}
        if payload:
            st.json(payload)

        action_cols = st.columns(4)
        with action_cols[0]:
            _status_button("Acknowledge", "acknowledged", alert["alert_id"], alert["status"] != "new")
        with action_cols[1]:
            _status_button(
                "Investigating",
                "investigating",
                alert["alert_id"],
                alert["status"] not in {"new", "acknowledged"},
            )
        with action_cols[2]:
            _status_button(
                "Resolved",
                "resolved",
                alert["alert_id"],
                alert["status"] in {"resolved", "dismissed"},
            )
        with action_cols[3]:
            _status_button(
                "Dismissed",
                "dismissed",
                alert["alert_id"],
                alert["status"] in {"resolved", "dismissed"},
            )

        if Path(__file__).with_name("08_recommendations.py").exists():
            st.page_link(
                "pages/08_recommendations.py",
                label="Ouvrir Recommendations",
            )
        else:
            st.caption("Lien Recommendations disponible quand la page 08 est installée.")
