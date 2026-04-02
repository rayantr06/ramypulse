"""Recommendation Center — Page Streamlit 08.

Genere des recommandations marketing actionnables via LLM externe
(Anthropic, OpenAI, ou Ollama local) depuis le contexte RamyPulse.

Sections :
  1. Generer maintenant
  2. Recommandations actives (cartes expandables)
  3. Historique des recommandations (tableau)
  4. Configuration de l'agent
"""

import logging

import pandas as pd
import streamlit as st

from config import (
    ANNOTATED_PARQUET_PATH,
    DEFAULT_AGENT_MODEL,
    DEFAULT_AGENT_PROVIDER,
    DEFAULT_CLIENT_ID,
    OLLAMA_BASE_URL,
)

logger = logging.getLogger(__name__)

st.set_page_config(page_title="Recommendation Center — RamyPulse", layout="wide")


# ─── Chargement des données ───────────────────────────────────────────────────

@st.cache_data(ttl=300)
def load_data() -> pd.DataFrame:
    """Charge annotated.parquet avec TTL 300 secondes.

    Returns:
        DataFrame annote, ou DataFrame vide si le fichier est absent.
    """
    try:
        df = pd.read_parquet(ANNOTATED_PARQUET_PATH)
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df["aspect"] = df["aspect"].fillna("")
        if "wilaya" in df.columns:
            df["wilaya"] = df["wilaya"].fillna("").str.lower().str.strip()
        return df
    except FileNotFoundError:
        return pd.DataFrame()


df = load_data()

# ─── Header ──────────────────────────────────────────────────────────────────

st.title("Recommendation Center")
st.caption("Genere des recommandations marketing actionnables a partir des donnees RamyPulse.")

if df.empty:
    st.warning("Donnees non disponibles. Lancez d'abord scripts/run_demo_05.py")
    st.stop()

# ─── Session state ────────────────────────────────────────────────────────────

if "reco_provider" not in st.session_state:
    st.session_state["reco_provider"] = DEFAULT_AGENT_PROVIDER
if "reco_model" not in st.session_state:
    st.session_state["reco_model"] = DEFAULT_AGENT_MODEL
if "reco_api_key" not in st.session_state:
    st.session_state["reco_api_key"] = ""


# ─── Section 1 — Générer maintenant ──────────────────────────────────────────

st.header("1. Generer des recommandations")

col_trigger, col_scope = st.columns([1, 2])

with col_trigger:
    trigger_type = st.selectbox(
        "Declencheur",
        options=["manual", "alert_triggered", "scheduled"],
        format_func=lambda x: {
            "manual": "Manuel (global)",
            "alert_triggered": "Depuis une alerte",
            "scheduled": "Rapport planifie",
        }.get(x, x),
    )

trigger_id = None
with col_scope:
    if trigger_type == "alert_triggered":
        raw_id = st.text_input("ID de l'alerte declencheuse", placeholder="UUID de l'alerte...")
        trigger_id = raw_id.strip() or None
    elif trigger_type == "scheduled":
        st.info("Mode planifie — utilise toutes les watchlists actives comme contexte.")

generate_btn = st.button("Generer les recommandations", type="primary")

if generate_btn:
    provider = st.session_state["reco_provider"]
    model = st.session_state["reco_model"] or None
    api_key = st.session_state["reco_api_key"] or None

    with st.spinner("Analyse en cours — assemblage du contexte, appel a l'agent..."):
        try:
            from core.recommendation.agent_client import generate_recommendations
            from core.recommendation.context_builder import build_recommendation_context
            from core.recommendation.recommendation_manager import save_recommendation

            context = build_recommendation_context(
                trigger_type=trigger_type,
                trigger_id=trigger_id,
                df_annotated=df,
                max_rag_chunks=8,
            )

            result = generate_recommendations(
                context=context,
                provider=provider,
                model=model,
                api_key=api_key,
            )

            save_recommendation(
                result=result,
                trigger_type=trigger_type,
                trigger_id=trigger_id,
            )

            if result.get("parse_success", True):
                nb = len(result.get("recommendations", []))
                ms = result.get("generation_ms", 0)
                conf = result.get("confidence_score", 0)
                st.success(
                    f"{nb} recommandation(s) generee(s) en {ms / 1000:.1f}s — "
                    f"confiance : {conf:.0%}"
                )
            else:
                st.warning(
                    "Le modele n'a pas retourne un JSON valide. "
                    "Resultats partiels affiches."
                )

            load_data.clear()
            st.rerun()

        except Exception as exc:
            st.error(f"Erreur lors de la generation : {exc}")
            logger.exception("Erreur generate_recommendations")

st.divider()


# ─── Section 2 — Recommandations actives ─────────────────────────────────────

st.header("2. Recommandations actives")

try:
    from core.recommendation.recommendation_manager import (
        list_recommendations,
        update_recommendation_status,
    )

    active_recos = list_recommendations(status="active", limit=10)

    if not active_recos:
        st.info("Aucune recommandation active. Generez-en une depuis la section 1.")
    else:
        for reco_row in active_recos:
            recs = reco_row.get("recommendations", [])
            summary = reco_row.get("analysis_summary", "")
            provider_label = reco_row.get("provider_used", "?")
            created_at = reco_row.get("created_at", "")[:19]
            confidence = reco_row.get("confidence_score") or 0.0
            rec_id = reco_row["recommendation_id"]

            header_label = (
                f"{len(recs)} reco(s) | confiance {confidence:.0%} | "
                f"provider: {provider_label} | {created_at}"
            )

            with st.expander(header_label, expanded=False):
                if summary:
                    st.markdown(f"**Situation :** {summary}")
                    st.divider()

                for rec in recs:
                    priority = rec.get("priority", "medium")
                    icons = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}
                    icon = icons.get(priority, "⚪")

                    st.markdown(f"#### {icon} [{priority.upper()}] {rec.get('title', '')}")

                    col_why, col_target = st.columns(2)
                    with col_why:
                        st.markdown(f"**Pourquoi :** {rec.get('rationale', '')}")
                        st.markdown(f"**Donnees :** _{rec.get('data_basis', 'N/A')}_")
                    with col_target:
                        st.markdown(
                            f"**Cible :** {rec.get('target_segment', 'N/A')} · "
                            f"{rec.get('target_platform', 'N/A')}"
                        )
                        regions = rec.get("target_regions", [])
                        if regions:
                            st.markdown(f"**Regions :** {', '.join(regions)}")

                    inf = rec.get("influencer_profile", {})
                    if inf and inf.get("tier") not in (None, "none", ""):
                        st.markdown(
                            f"**Influenceur :** Tier {inf.get('tier', '?')} | "
                            f"Niche : {inf.get('niche', '?')} | "
                            f"Ton : {inf.get('tone', '?')}"
                        )

                    content = rec.get("content", {})
                    hooks = content.get("hooks", [])
                    if hooks:
                        st.markdown("**Hooks creatifs :**")
                        for hook in hooks:
                            st.markdown(f"- {hook}")

                    script = content.get("script_outline", "")
                    if script:
                        st.markdown(f"**Script :** {script}")

                    timing = rec.get("timing", {})
                    if timing:
                        st.markdown(
                            f"**Timing :** {timing.get('urgency', '?')} — "
                            f"{timing.get('best_moment', '')}"
                        )

                    kpis = rec.get("kpi_to_track", [])
                    if kpis:
                        st.markdown(f"**KPIs :** {' | '.join(kpis)}")

                    st.divider()

                col_a1, col_a2, col_a3 = st.columns(3)
                with col_a1:
                    if st.button("Archiver", key=f"archive_{rec_id}"):
                        try:
                            update_recommendation_status(rec_id, "archived")
                            st.success("Archive.")
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Erreur : {exc}")
                with col_a2:
                    if st.button("Rejeter", key=f"dismiss_{rec_id}"):
                        try:
                            update_recommendation_status(rec_id, "dismissed")
                            st.success("Rejete.")
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Erreur : {exc}")
                with col_a3:
                    st.caption(f"ID : {rec_id[:8]}...")

except Exception as exc:
    st.error(f"Impossible de charger les recommandations : {exc}")
    logger.exception("Erreur chargement recommandations actives")

st.divider()


# ─── Section 3 — Historique ──────────────────────────────────────────────────

st.header("3. Historique")

try:
    from core.recommendation.recommendation_manager import list_recommendations as _list_all

    all_recos = _list_all(limit=50)

    if not all_recos:
        st.info("Aucune recommandation dans l'historique.")
    else:
        hist_rows = []
        for r in all_recos:
            hist_rows.append({
                "Date": r.get("created_at", "")[:19],
                "Declencheur": r.get("trigger_type", ""),
                "# Reco": len(r.get("recommendations", [])),
                "Confiance": f"{(r.get('confidence_score') or 0):.0%}",
                "Provider": r.get("provider_used", ""),
                "Modele": r.get("model_used", ""),
                "Statut": r.get("status", ""),
            })
        st.dataframe(pd.DataFrame(hist_rows), use_container_width=True)

except Exception as exc:
    st.error(f"Erreur chargement historique : {exc}")

st.divider()


# ─── Section 4 — Configuration ───────────────────────────────────────────────

st.header("4. Configuration de l'agent")

with st.form("agent_config_form"):
    col_prov, col_mod = st.columns(2)

    with col_prov:
        provider_options = ["ollama_local", "anthropic", "openai"]
        try:
            current_idx = provider_options.index(st.session_state["reco_provider"])
        except ValueError:
            current_idx = 0
        selected_provider = st.selectbox(
            "Provider LLM",
            options=provider_options,
            index=current_idx,
            format_func=lambda x: {
                "ollama_local": "Ollama local",
                "anthropic": "Anthropic (Claude)",
                "openai": "OpenAI (GPT)",
            }.get(x, x),
        )

    with col_mod:
        model_defaults = {
            "ollama_local": "qwen2.5:14b",
            "anthropic": "claude-sonnet-4-6",
            "openai": "gpt-4o",
        }
        selected_model = st.text_input(
            "Modele",
            value=st.session_state.get("reco_model") or model_defaults.get(selected_provider, ""),
            placeholder=model_defaults.get(selected_provider, ""),
        )

    if selected_provider in ("anthropic", "openai"):
        api_key_input = st.text_input(
            f"Cle API {selected_provider.capitalize()}",
            value=st.session_state.get("reco_api_key", ""),
            type="password",
            help="La cle n'est jamais affichee en clair ni stockee en base.",
        )
    else:
        api_key_input = ""
        st.info(f"Ollama local — URL : {OLLAMA_BASE_URL} — aucune cle requise.")

    submitted = st.form_submit_button("Sauvegarder la configuration")
    if submitted:
        st.session_state["reco_provider"] = selected_provider
        st.session_state["reco_model"] = selected_model
        st.session_state["reco_api_key"] = api_key_input
        st.success(
            f"Configuration sauvegardee : {selected_provider} / {selected_model or 'defaut'}"
        )
