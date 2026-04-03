"""Shared Streamlit runtime diagnostics panel."""

from __future__ import annotations

import streamlit as st


def render_runtime_panel(diagnostics: dict, *, title: str = "Etat runtime", expanded: bool = False) -> None:
    """Render a compact runtime diagnostics expander."""
    annotation = diagnostics.get("annotation", {})
    rag = diagnostics.get("rag", {})
    recommendation = diagnostics.get("recommendation", {})

    with st.expander(title, expanded=expanded):
        top_cols = st.columns(4)
        top_cols[0].metric("Mode", diagnostics.get("mode", "-"))
        top_cols[1].metric("Annotation", "Local" if annotation.get("local_model_available") else "Fallback")
        top_cols[2].metric("Index RAG", "Pret" if rag.get("index_ready") else "Absent")
        top_cols[3].metric("Reco API", "OK" if recommendation.get("api_configured") else "A configurer")

        st.caption(
            f"Annotation: {annotation.get('backend_label', '-')} | "
            f"RAG: {rag.get('provider', '-')} / {rag.get('model', '-')} | "
            f"Reco: {recommendation.get('provider', '-')} / {recommendation.get('model', '-')}"
        )

        if annotation.get("details"):
            st.write(annotation["details"])
