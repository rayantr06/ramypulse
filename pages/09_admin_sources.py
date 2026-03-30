"""Page Streamlit d'administration des sources surveillees."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import DatabaseManager
from core.source_registry import SourceRegistry
from pages.phase1_admin_helpers import (
    build_sources_frame,
    compute_source_metrics,
    filter_source_records,
)


@st.cache_resource
def _get_registry() -> SourceRegistry:
    """Initialise la base SQLite et retourne le registre de sources."""
    database = DatabaseManager()
    database.create_tables()
    return SourceRegistry(database)


def _render_create_source_form(registry: SourceRegistry) -> None:
    """Affiche un formulaire minimal de creation de source."""
    with st.form("create_source"):
        st.subheader("Ajouter une source")
        col1, col2 = st.columns(2)
        with col1:
            platform = st.selectbox(
                "Plateforme",
                options=["facebook", "instagram", "google_maps", "youtube", "sav", "import"],
            )
            source_type = st.text_input("Source type", value=f"{platform}_page")
            display_name = st.text_input("Nom affiche")
            owner_type = st.selectbox(
                "Owner type",
                options=["owned", "competitor", "market"],
            )
        with col2:
            external_id = st.text_input("External ID")
            url = st.text_input("URL")
            brand = st.text_input("Brand")
            sync_frequency = st.selectbox(
                "Frequence",
                options=["hourly", "daily", "weekly", "manual"],
                index=1,
            )

        submitted = st.form_submit_button("Creer la source")
        if submitted:
            try:
                registry.create_source(
                    {
                        "platform": platform,
                        "source_type": source_type,
                        "display_name": display_name,
                        "external_id": external_id or None,
                        "url": url or None,
                        "owner_type": owner_type,
                        "brand": brand or None,
                        "sync_frequency": sync_frequency,
                        "auth_mode": "manual",
                    }
                )
                st.success("Source creee.")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))


def _render_source_actions(registry: SourceRegistry, records: list[dict]) -> None:
    """Affiche les actions de cycle de vie sur les sources existantes."""
    st.subheader("Actions")
    if not records:
        st.info("Aucune source a administrer pour le moment.")
        return

    selected_source_id = st.selectbox(
        "Selectionner une source",
        options=[row["source_id"] for row in records],
        format_func=lambda value: next(
            (
                f"{row['display_name']} ({row['platform']})"
                for row in records
                if row["source_id"] == value
            ),
            value,
        ),
    )
    selected_source = next(row for row in records if row["source_id"] == selected_source_id)

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Marquer sync", use_container_width=True):
            registry.mark_sync(selected_source_id)
            st.success("Horodatage de sync mis a jour.")
            st.rerun()
    with col2:
        if selected_source.get("is_active"):
            if st.button("Desactiver", use_container_width=True):
                registry.deactivate_source(selected_source_id)
                st.success("Source desactivee.")
                st.rerun()
        else:
            if st.button("Reactiver", use_container_width=True):
                registry.reactivate_source(selected_source_id)
                st.success("Source reactivee.")
                st.rerun()
    with col3:
        st.caption("Suppression non exposee ici pour rester conservative.")


def main() -> None:
    """Rendu de la page Admin Sources."""
    st.title("Admin Sources")

    registry = _get_registry()
    records = registry.list_sources()
    metrics = compute_source_metrics(records)

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Total", metrics["total"])
    kpi2.metric("Actives", metrics["active"])
    kpi3.metric("Inactives", metrics["inactive"])
    kpi4.metric("Plateformes", metrics["platforms"])

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

    filtered_records = filter_source_records(records, platform=platform, owner_type=owner_type, status=status)
    frame = build_sources_frame(filtered_records)

    st.subheader("Sources enregistrees")
    if frame.empty:
        st.info("La base SQLite ne contient encore aucune source.")
    else:
        st.dataframe(frame, use_container_width=True, hide_index=True)

    st.divider()
    left, right = st.columns([3, 2])
    with left:
        _render_create_source_form(registry)
    with right:
        _render_source_actions(registry, records)


main()
