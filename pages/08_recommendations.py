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
from core.recommendation.agent_client import MODEL_CATALOG
from core.security.secret_manager import is_secret_reference, resolve_secret, store_secret

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

try:
    from core.recommendation.recommendation_manager import (
        get_client_agent_config,
        get_recommendation,
        list_recommendations,
        save_recommendation,
        update_client_agent_config,
        update_recommendation_status,
    )

    agent_config = get_client_agent_config(client_id=DEFAULT_CLIENT_ID)
except Exception as exc:
    st.error(f"Impossible de charger la configuration agent: {exc}")
    st.stop()

if "reco_provider" not in st.session_state:
    st.session_state["reco_provider"] = agent_config.get("provider") or DEFAULT_AGENT_PROVIDER
if "reco_model" not in st.session_state:
    st.session_state["reco_model"] = agent_config.get("model") or DEFAULT_AGENT_MODEL
if "reco_api_key" not in st.session_state:
    st.session_state["reco_api_key"] = ""
if "reco_api_key_reference" not in st.session_state:
    st.session_state["reco_api_key_reference"] = agent_config.get("api_key_encrypted") or ""
if "reco_auto_trigger_on_alert" not in st.session_state:
    st.session_state["reco_auto_trigger_on_alert"] = bool(agent_config.get("auto_trigger_on_alert"))
if "reco_auto_trigger_severity" not in st.session_state:
    st.session_state["reco_auto_trigger_severity"] = agent_config.get("auto_trigger_severity", "critical")
if "reco_weekly_enabled" not in st.session_state:
    st.session_state["reco_weekly_enabled"] = bool(agent_config.get("weekly_report_enabled"))
if "reco_weekly_day" not in st.session_state:
    st.session_state["reco_weekly_day"] = int(agent_config.get("weekly_report_day") or 1)

focused_recommendation_id = str(st.query_params.get("recommendation_id") or "").strip() or None
if focused_recommendation_id:
    focused_recommendation = get_recommendation(focused_recommendation_id)
    if focused_recommendation:
        st.info(
            "Recommendation ciblee: "
            f"{focused_recommendation_id[:8]}... | "
            f"{focused_recommendation.get('analysis_summary') or 'Sans resume'}"
        )


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

col_gen, col_prev = st.columns([2, 1])
generate_btn = col_gen.button("Generer les recommandations", type="primary")
preview_btn = col_prev.button("Previsualiser le contexte client")

if preview_btn:
    with st.spinner("Assemblage du contexte..."):
        try:
            from core.recommendation.context_builder import build_recommendation_context
            ctx = build_recommendation_context(
                trigger_type=trigger_type,
                trigger_id=trigger_id,
                df_annotated=df,
                max_rag_chunks=8,
            )
            metrics = ctx.get("current_metrics", {})
            st.markdown("#### Contexte qui sera envoyé au LLM")
            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.metric("NSS global", f"{metrics.get('nss_global') or 0:.1f}")
            col_m2.metric("Volume signaux", metrics.get("volume_total", 0))
            col_m3.metric("Tokens estimés", ctx.get("estimated_tokens", 0))

            col_d1, col_d2, col_d3 = st.columns(3)
            col_d1.metric("Alertes actives", len(ctx.get("active_alerts", [])))
            col_d2.metric("Watchlists actives", len(ctx.get("active_watchlists", [])))
            col_d3.metric("Campagnes récentes", len(ctx.get("recent_campaigns", [])))

            rag = ctx.get("rag_chunks", [])
            if rag:
                st.success(f"{len(rag)} extraits RAG chargés depuis l'index FAISS")
            else:
                st.info("Aucun chunk RAG (index FAISS absent ou vide — le LLM utilisera uniquement les métriques)")

            top_neg = metrics.get("top_negative_aspects", [])
            if top_neg:
                st.warning(f"Aspects les plus problématiques : **{', '.join(top_neg)}**")

            with st.expander("Voir NSS par aspect"):
                asp_data = metrics.get("nss_by_aspect", {})
                if asp_data:
                    import pandas as _pd
                    asp_df = _pd.DataFrame(
                        [(k, v) for k, v in asp_data.items() if v is not None],
                        columns=["Aspect", "NSS"],
                    ).sort_values("NSS")
                    st.bar_chart(asp_df.set_index("Aspect")["NSS"])
        except Exception as exc:
            st.error(f"Erreur assemblage contexte : {exc}")

if generate_btn:
    provider = st.session_state["reco_provider"]
    model = st.session_state["reco_model"] or None
    raw_api_key = st.session_state["reco_api_key"] or None
    if raw_api_key and is_secret_reference(raw_api_key):
        api_key = resolve_secret(raw_api_key)
    elif raw_api_key:
        api_key = raw_api_key
    else:
        api_key = resolve_secret(st.session_state.get("reco_api_key_reference"))

    with st.spinner("Analyse en cours — assemblage du contexte, appel a l'agent..."):
        try:
            from core.recommendation.agent_client import generate_recommendations
            from core.recommendation.context_builder import build_recommendation_context

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

            with st.expander(header_label, expanded=(focused_recommendation_id == rec_id)):
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
                    if reco_row.get("alert_id"):
                        st.caption(f"Alerte source : {reco_row['alert_id'][:8]}...")
                    if st.button("Creer une campagne depuis cette reco", key=f"campaign_link_{rec_id}"):
                        st.query_params["recommendation_id"] = rec_id
                        st.switch_page("pages/05_campaigns.py")

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
        catalog_for_provider = MODEL_CATALOG.get(selected_provider, [])
        catalog_ids = [m["id"] for m in catalog_for_provider]
        catalog_labels = {m["id"]: m["label"] for m in catalog_for_provider}

        current_model = st.session_state.get("reco_model") or ""
        use_custom = current_model not in catalog_ids and current_model != ""

        model_select_options = catalog_ids + (["autre..."] if catalog_ids else [])
        try:
            default_sel_idx = catalog_ids.index(current_model) if current_model in catalog_ids else 0
        except ValueError:
            default_sel_idx = 0

        selected_from_catalog = st.selectbox(
            "Modele",
            options=model_select_options,
            index=default_sel_idx,
            format_func=lambda x: catalog_labels.get(x, x),
            key=f"model_catalog_{selected_provider}",
        )

        if selected_from_catalog == "autre...":
            selected_model = st.text_input(
                "ID du modele personnalise",
                value=current_model if use_custom else "",
                placeholder="Ex: claude-opus-4-6, gpt-4o, mistral:latest",
            )
        else:
            selected_model = selected_from_catalog
            if not selected_model and catalog_ids:
                selected_model = catalog_ids[0]

    col_auto, col_weekly = st.columns(2)
    with col_auto:
        auto_trigger_on_alert = st.checkbox(
            "Auto-trigger sur alertes",
            value=bool(st.session_state.get("reco_auto_trigger_on_alert", False)),
        )
        severity_options = ["low", "medium", "high", "critical"]
        selected_auto_severity = st.selectbox(
            "Severite minimale auto-trigger",
            options=severity_options,
            index=severity_options.index(st.session_state.get("reco_auto_trigger_severity", "critical")),
        )
    with col_weekly:
        weekly_enabled = st.checkbox(
            "Rapport hebdo active",
            value=bool(st.session_state.get("reco_weekly_enabled", False)),
        )
        weekly_day = st.selectbox(
            "Jour du rapport hebdo",
            options=[1, 2, 3, 4, 5, 6, 7],
            format_func=lambda value: {
                1: "Lundi",
                2: "Mardi",
                3: "Mercredi",
                4: "Jeudi",
                5: "Vendredi",
                6: "Samedi",
                7: "Dimanche",
            }[value],
            index=max(0, min(6, int(st.session_state.get("reco_weekly_day", 1)) - 1)),
        )

    if selected_provider in ("anthropic", "openai"):
        stored_reference = (
            st.session_state.get("reco_api_key_reference")
            or agent_config.get("api_key_encrypted")
            or ""
        )
        if stored_reference:
            st.caption(f"Reference secret actuellement stockee: {stored_reference}")
        api_key_input = st.text_input(
            f"Cle API {selected_provider.capitalize()}",
            value=st.session_state.get("reco_api_key", ""),
            type="password",
            help="La cle ou reference est persistée pour l'auto-trigger.",
        )
    else:
        api_key_input = ""
        st.info(f"Ollama local — URL : {OLLAMA_BASE_URL} — aucune cle requise.")

    submitted = st.form_submit_button("Sauvegarder la configuration")
    if submitted:
        st.session_state["reco_provider"] = selected_provider
        st.session_state["reco_model"] = selected_model
        st.session_state["reco_auto_trigger_on_alert"] = auto_trigger_on_alert
        st.session_state["reco_auto_trigger_severity"] = selected_auto_severity
        st.session_state["reco_weekly_enabled"] = weekly_enabled
        st.session_state["reco_weekly_day"] = weekly_day
        try:
            if selected_provider in ("anthropic", "openai"):
                if api_key_input.strip():
                    secret_reference = store_secret(api_key_input.strip(), label=selected_provider)
                else:
                    secret_reference = (
                        st.session_state.get("reco_api_key_reference")
                        or agent_config.get("api_key_encrypted")
                        or None
                    )
            else:
                secret_reference = None

            persisted = update_client_agent_config(
                {
                    "provider": selected_provider,
                    "model": selected_model or None,
                    "api_key_encrypted": secret_reference,
                    "auto_trigger_on_alert": auto_trigger_on_alert,
                    "auto_trigger_severity": selected_auto_severity,
                    "weekly_report_enabled": weekly_enabled,
                    "weekly_report_day": weekly_day,
                },
                client_id=DEFAULT_CLIENT_ID,
            )
            st.session_state["reco_api_key_reference"] = persisted.get("api_key_encrypted") or ""
            st.session_state["reco_api_key"] = ""
            st.success(
                "Configuration sauvegardee : "
                f"{persisted['provider']} / {persisted.get('model') or 'defaut'}"
            )
        except Exception as exc:
            st.error(f"Impossible de sauvegarder la configuration : {exc}")
