"""Page Streamlit d'administration des sources surveillées."""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from config import DEFAULT_CLIENT_ID
from core.ingestion.health_checker import compute_source_health
from core.ingestion.orchestrator import IngestionOrchestrator
from core.ingestion.source_admin_service import SourceAdminService
from core.runtime.diagnostics import collect_runtime_diagnostics
from ui_helpers.runtime_panel import render_runtime_panel
from ui_helpers.source_admin_helpers import (
    build_health_snapshots_frame,
    build_source_sync_runs_frame,
    build_sources_frame,
    compute_source_metrics,
    filter_source_records,
)

st.set_page_config(page_title="Admin Sources — RamyPulse", layout="wide")


@st.cache_resource
def _get_services() -> tuple[IngestionOrchestrator, SourceAdminService]:
    orchestrator = IngestionOrchestrator()
    service = SourceAdminService()
    return orchestrator, service


@st.cache_data(ttl=60, show_spinner=False)
def load_runtime_diagnostics() -> dict:
    return collect_runtime_diagnostics()


def _parse_json_mapping(raw: str) -> dict[str, str] | None:
    if not raw.strip():
        return None
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError("Le mapping JSON doit être un objet.")
    return {str(key): str(value) for key, value in parsed.items()}


def _render_create_source_form(orchestrator: IngestionOrchestrator) -> None:
    with st.form("create_source", clear_on_submit=True):
        st.subheader("Ajouter une source PRD")
        left, right = st.columns(2)
        with left:
            source_name = st.text_input("Nom source", placeholder="Ex : Facebook Ramy Oran")
            platform = st.selectbox("Plateforme", ["facebook", "google_maps", "youtube", "import"])
            source_type = st.text_input("Source type", value="batch_import" if platform == "import" else f"{platform}_feed")
            owner_type = st.selectbox("Owner type", ["owned", "competitor", "market"])
            auth_mode = st.selectbox("Auth mode", ["public", "file_upload", "token", "manual"])
        with right:
            sync_frequency_minutes = st.number_input("Fréquence sync (minutes)", min_value=5, value=60, step=5)
            freshness_sla_hours = st.number_input("SLA fraîcheur (heures)", min_value=1, value=24, step=1)
            snapshot_path = st.text_input("Snapshot path / import path", placeholder=str(Path("data/raw/facebook_raw.parquet")))
            mapping_raw = st.text_area(
                "Mapping JSON optionnel",
                value='{"review": "text"}' if platform == "import" else "",
                height=90,
            )

        submitted = st.form_submit_button("Créer la source", use_container_width=True)
        if not submitted:
            return

        try:
            config_json: dict[str, object] = {}
            if snapshot_path.strip():
                config_json["snapshot_path"] = snapshot_path.strip()
            parsed_mapping = _parse_json_mapping(mapping_raw)
            if parsed_mapping:
                config_json["column_mapping"] = parsed_mapping

            orchestrator.create_source(
                {
                    "client_id": DEFAULT_CLIENT_ID,
                    "source_name": source_name,
                    "platform": platform,
                    "source_type": source_type,
                    "owner_type": owner_type,
                    "auth_mode": auth_mode,
                    "sync_frequency_minutes": int(sync_frequency_minutes),
                    "freshness_sla_hours": int(freshness_sla_hours),
                    "config_json": config_json,
                }
            )
        except Exception as exc:  # pragma: no cover - garde-fou UI
            st.error(f"Impossible de créer la source : {exc}")
            return

        st.success("Source créée.")
        st.rerun()


def _render_source_actions(
    orchestrator: IngestionOrchestrator,
    service: SourceAdminService,
    records: list[dict],
) -> None:
    st.subheader("Actions")
    if not records:
        st.info("Aucune source à administrer pour le moment.")
        return

    selected_source_id = st.selectbox(
        "Sélectionner une source",
        options=[row["source_id"] for row in records],
        format_func=lambda value: next(
            (
                f"{row['source_name']} ({row['platform']})"
                for row in records
                if row["source_id"] == value
            ),
            value,
        ),
        key="admin_sources_selected_source",
    )
    selected_source = service.get_source_trace(selected_source_id, client_id=DEFAULT_CLIENT_ID)
    source_config = selected_source.get("config_json") or {}

    manual_file_path = st.text_input(
        "Chemin fichier manuel",
        value=str(source_config.get("snapshot_path") or ""),
        help="Utilisé pour les sources import et les snapshots locaux de connecteurs plateforme.",
    )

    columns = st.columns(4)
    if columns[0].button("Lancer sync", use_container_width=True):
        try:
            orchestrator.run_source_sync(
                selected_source_id,
                manual_file_path=manual_file_path or None,
                client_id=DEFAULT_CLIENT_ID,
            )
            st.success("Synchronisation lancée.")
            st.rerun()
        except Exception as exc:  # pragma: no cover
            st.error(f"Echec sync : {exc}")

    if columns[1].button("Calculer santé", use_container_width=True):
        try:
            compute_source_health(selected_source_id, client_id=DEFAULT_CLIENT_ID)
            st.success("Snapshot de santé calculé.")
            st.rerun()
        except Exception as exc:  # pragma: no cover
            st.error(f"Echec calcul santé : {exc}")

    if bool(selected_source.get("is_active")):
        if columns[2].button("Désactiver", use_container_width=True):
            try:
                service.update_source(selected_source_id, {"is_active": 0}, client_id=DEFAULT_CLIENT_ID)
                st.success("Source désactivée.")
                st.rerun()
            except Exception as exc:  # pragma: no cover
                st.error(f"Echec désactivation : {exc}")
    else:
        if columns[2].button("Réactiver", use_container_width=True):
            try:
                service.update_source(selected_source_id, {"is_active": 1}, client_id=DEFAULT_CLIENT_ID)
                st.success("Source réactivée.")
                st.rerun()
            except Exception as exc:  # pragma: no cover
                st.error(f"Echec réactivation : {exc}")

    columns[3].caption("Les suppressions restent interdites depuis l'UI.")

    trace = service.get_source_trace(selected_source_id, client_id=DEFAULT_CLIENT_ID)
    st.markdown("**Trace pipeline**")
    trace_cols = st.columns(3)
    trace_cols[0].metric("Raw documents", int(trace.get("raw_document_count") or 0))
    trace_cols[1].metric("Normalized", int(trace.get("normalized_count") or 0))
    trace_cols[2].metric("Enriched", int(trace.get("enriched_count") or 0))

    with st.expander("Détail source sélectionnée", expanded=False):
        st.json(trace)


def main() -> None:
    st.title("Admin Sources")
    st.caption(f"Administration Wave 5.1 des sources PRD pour le client {DEFAULT_CLIENT_ID}.")
    render_runtime_panel(load_runtime_diagnostics(), title="État runtime", expanded=False)

    orchestrator, service = _get_services()
    records = service.list_sources(client_id=DEFAULT_CLIENT_ID)
    sync_runs = service.list_sync_runs(client_id=DEFAULT_CLIENT_ID, limit=25)
    health_rows = service.list_health_snapshots(client_id=DEFAULT_CLIENT_ID, limit=25)
    metrics = compute_source_metrics(records)

    kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
    kpi1.metric("Total", metrics["total"])
    kpi2.metric("Actives", metrics["active"])
    kpi3.metric("Inactives", metrics["inactive"])
    kpi4.metric("Plateformes", metrics["platforms"])
    kpi5.metric("Dégradées", metrics["degraded"])

    st.divider()
    filter_cols = st.columns(3)
    with filter_cols[0]:
        platform = st.selectbox(
            "Plateforme",
            options=["all"] + sorted({row["platform"] for row in records if row.get("platform")}),
        )
    with filter_cols[1]:
        owner_type = st.selectbox(
            "Owner type",
            options=["all"] + sorted({row["owner_type"] for row in records if row.get("owner_type")}),
        )
    with filter_cols[2]:
        status = st.selectbox("Statut", options=["all", "active", "inactive"])

    filtered_records = filter_source_records(
        records,
        platform=platform,
        owner_type=owner_type,
        status=status,
    )
    sources_frame = build_sources_frame(filtered_records)
    runs_frame = build_source_sync_runs_frame(sync_runs)
    health_frame = build_health_snapshots_frame(health_rows)

    sources_tab, runs_tab, health_tab = st.tabs(
        ["Sources", "Sync runs", "Health snapshots"]
    )
    with sources_tab:
        if sources_frame.empty:
            st.info("Aucune source enregistrée.")
        else:
            st.dataframe(sources_frame, use_container_width=True, hide_index=True)
    with runs_tab:
        if runs_frame.empty:
            st.info("Aucun run de synchronisation disponible.")
        else:
            st.dataframe(runs_frame, use_container_width=True, hide_index=True)
    with health_tab:
        if health_frame.empty:
            st.info("Aucun snapshot de santé disponible.")
        else:
            st.dataframe(health_frame, use_container_width=True, hide_index=True)

    st.divider()
    left, right = st.columns([2, 3])
    with left:
        _render_create_source_form(orchestrator)
    with right:
        _render_source_actions(orchestrator, service, records)


main()
