"""Page Streamlit Campaign Intelligence."""

from __future__ import annotations

import sqlite3

import pandas as pd
import streamlit as st

from config import ANNOTATED_PARQUET_PATH, SQLITE_DB_PATH

st.set_page_config(page_title="Campagnes - RamyPulse", layout="wide")


@st.cache_data(ttl=300)
def load_data() -> pd.DataFrame:
    """Charge annotated.parquet avec normalisation minimale."""
    try:
        dataframe = pd.read_parquet(ANNOTATED_PARQUET_PATH)
    except FileNotFoundError:
        return pd.DataFrame()

    if "timestamp" in dataframe.columns:
        dataframe["timestamp"] = pd.to_datetime(dataframe["timestamp"], errors="coerce")
    if "wilaya" in dataframe.columns:
        dataframe["wilaya"] = dataframe["wilaya"].fillna("").str.lower().str.strip()
    if "aspect" in dataframe.columns:
        dataframe["aspect"] = dataframe["aspect"].fillna("")
    return dataframe


def load_campaign_snapshots(campaign_id: str) -> pd.DataFrame:
    """Charge les derniers snapshots persistés d'une campagne."""
    with sqlite3.connect(SQLITE_DB_PATH) as connection:
        return pd.read_sql_query(
            """
            SELECT phase, metric_date, nss_filtered, nss_baseline, nss_uplift,
                   volume_filtered, volume_baseline, volume_lift_pct, computed_at
            FROM campaign_metrics_snapshots
            WHERE campaign_id = ?
            ORDER BY computed_at DESC, phase ASC
            """,
            connection,
            params=(campaign_id,),
        )


def load_campaign_signal_links(campaign_id: str, limit: int = 10) -> pd.DataFrame:
    """Charge les signaux attribués les plus forts pour une campagne."""
    with sqlite3.connect(SQLITE_DB_PATH) as connection:
        return pd.read_sql_query(
            """
            SELECT phase, signal_id, attribution_score, attributed_at
            FROM campaign_signal_links
            WHERE campaign_id = ?
            ORDER BY attribution_score DESC, attributed_at DESC
            LIMIT ?
            """,
            connection,
            params=(campaign_id, limit),
        )


def _clear_recommendation_query_param() -> None:
    """Supprime le query param recommendation_id si présent."""
    if "recommendation_id" in st.query_params:
        del st.query_params["recommendation_id"]


df = load_data()

st.title("Campaign Intelligence")
st.caption("Creez et mesurez l'impact de vos campagnes marketing sur les metriques NSS.")

try:
    from core.campaigns.campaign_manager import (
        create_campaign,
        delete_campaign,
        list_campaigns,
        update_campaign_status,
    )
    from core.campaigns.campaign_prefill import (
        build_campaign_form_defaults,
        build_campaign_prefill_from_recommendation_record,
    )
    from core.campaigns.impact_calculator import compute_campaign_impact
    from core.recommendation.recommendation_manager import get_recommendation

    campaigns = list_campaigns(limit=100)
except Exception as exc:
    st.error(f"Erreur SQLite : {exc}")
    st.stop()

source_recommendation_id = str(st.query_params.get("recommendation_id") or "").strip() or None
campaign_form_defaults = build_campaign_form_defaults({})
recommendation_source = None

if source_recommendation_id:
    recommendation_source = get_recommendation(source_recommendation_id)
    if recommendation_source:
        campaign_form_defaults = build_campaign_form_defaults(
            build_campaign_prefill_from_recommendation_record(recommendation_source)
        )
        st.info(
            "Creation depuis recommendation: "
            f"{source_recommendation_id[:8]}... | "
            f"{recommendation_source.get('analysis_summary') or 'Sans resume'}"
        )
        if st.button("Effacer le pre-remplissage recommande", key="clear_reco_prefill"):
            _clear_recommendation_query_param()
            st.rerun()
    else:
        st.warning(f"Recommendation introuvable: {source_recommendation_id}")
        _clear_recommendation_query_param()

tab_list, tab_create, tab_impact = st.tabs(["Campagnes", "Nouvelle campagne", "Impact"])

with tab_list:
    st.subheader("Campagnes enregistrees")

    if not campaigns:
        st.info("Aucune campagne enregistree. Creez-en une dans l'onglet Nouvelle campagne.")
    else:
        status_filter = st.selectbox(
            "Filtrer par statut",
            ["Tous", "planned", "active", "completed", "cancelled"],
            key="status_filter",
        )
        filtered = [camp for camp in campaigns if status_filter == "Tous" or camp["status"] == status_filter]

        for camp in filtered:
            with st.expander(f"{camp['campaign_name']} - {camp['status'].upper()}", expanded=False):
                col1, col2, col3 = st.columns(3)
                col1.metric("Type", camp.get("campaign_type") or "-")
                col2.metric("Plateforme", camp.get("platform") or "-")
                col3.metric("Budget (DZA)", f"{camp.get('budget_dza') or 0:,}")

                col4, col5 = st.columns(2)
                col4.write(f"**Debut :** {camp.get('start_date') or '-'}")
                col5.write(f"**Fin :** {camp.get('end_date') or '-'}")

                if camp.get("target_segment"):
                    st.write(f"**Segment :** {camp['target_segment']}")
                if camp.get("target_aspects"):
                    st.write(f"**Aspects cibles :** {', '.join(camp['target_aspects'])}")
                if camp.get("target_regions"):
                    st.write(f"**Regions :** {', '.join(camp['target_regions'])}")
                if camp.get("keywords"):
                    st.write(f"**Mots-cles :** {', '.join(camp['keywords'])}")

                col_status, col_del = st.columns([3, 1])
                with col_status:
                    status_options = ["planned", "active", "completed", "cancelled"]
                    new_status = st.selectbox(
                        "Changer statut",
                        status_options,
                        index=status_options.index(camp["status"]),
                        key=f"status_{camp['campaign_id']}",
                    )
                    if st.button("Mettre a jour", key=f"upd_{camp['campaign_id']}"):
                        try:
                            update_campaign_status(camp["campaign_id"], new_status)
                        except Exception as exc:
                            st.error(f"Erreur : {exc}")
                        else:
                            st.success("Statut mis a jour.")
                            st.rerun()
                with col_del:
                    if st.button("Supprimer", key=f"del_{camp['campaign_id']}"):
                        try:
                            delete_campaign(camp["campaign_id"])
                        except Exception as exc:
                            st.error(f"Erreur : {exc}")
                        else:
                            st.success("Campagne supprimee.")
                            st.rerun()

with tab_create:
    st.subheader("Nouvelle campagne")
    if recommendation_source:
        st.caption(
            "Le formulaire est pre-rempli depuis la recommendation "
            f"{source_recommendation_id[:8]}..."
        )

    with st.form("form_create_campaign"):
        campaign_type_options = ["influencer", "paid_ad", "sponsoring", "launch", "promotion", "organic"]
        platform_options = ["instagram", "facebook", "youtube", "tiktok", "offline", "multi_platform"]
        influencer_tier_options = ["none", "nano", "micro", "macro", "mega"]

        col1, col2 = st.columns(2)
        campaign_name = col1.text_input(
            "Nom de la campagne *",
            value=campaign_form_defaults["campaign_name"],
            placeholder="Ex : Influenceur Oran Ramadan 2026",
        )
        campaign_type = col2.selectbox(
            "Type",
            campaign_type_options,
            index=(
                campaign_type_options.index(campaign_form_defaults["campaign_type"])
                if campaign_form_defaults["campaign_type"] in campaign_type_options
                else campaign_type_options.index("promotion")
            ),
        )

        col3, col4 = st.columns(2)
        platform = col3.selectbox(
            "Plateforme",
            platform_options,
            index=(
                platform_options.index(campaign_form_defaults["platform"])
                if campaign_form_defaults["platform"] in platform_options
                else platform_options.index("multi_platform")
            ),
        )
        influencer_tier = col4.selectbox(
            "Tier influenceur",
            influencer_tier_options,
            index=(
                influencer_tier_options.index(campaign_form_defaults["influencer_tier"])
                if campaign_form_defaults["influencer_tier"] in influencer_tier_options
                else 0
            ),
        )

        influencer_handle = st.text_input(
            "Handle influenceur",
            value=campaign_form_defaults["influencer_handle"],
            placeholder="@nomhandle",
        )
        description = st.text_area("Description", value=campaign_form_defaults["description"], height=80)
        target_segment = st.text_input(
            "Segment cible",
            value=campaign_form_defaults["target_segment"],
            placeholder="Ex : gen_z_18_25",
        )

        col5, col6 = st.columns(2)
        start_date = col5.date_input("Date de debut", value=campaign_form_defaults["start_date"])
        end_date = col6.date_input("Date de fin", value=campaign_form_defaults["end_date"])

        col7, col8 = st.columns(2)
        pre_window = col7.number_input(
            "Fenetre pre-campagne (jours)",
            min_value=1,
            max_value=90,
            value=int(campaign_form_defaults["pre_window_days"]),
        )
        post_window = col8.number_input(
            "Fenetre post-campagne (jours)",
            min_value=1,
            max_value=90,
            value=int(campaign_form_defaults["post_window_days"]),
        )

        budget = st.number_input("Budget (DZA)", min_value=0, value=0, step=10000)

        target_aspects_raw = st.text_input(
            "Aspects cibles (separes par virgule)",
            value=campaign_form_defaults["target_aspects_text"],
            placeholder="emballage, gout",
        )
        target_regions_raw = st.text_input(
            "Regions cibles (separees par virgule)",
            value=campaign_form_defaults["target_regions_text"],
            placeholder="oran, alger",
        )
        keywords_raw = st.text_input(
            "Mots-cles (separes par virgule)",
            value=campaign_form_defaults["keywords_text"],
            placeholder="ramy, jus, bouteille",
        )

        submitted = st.form_submit_button("Creer la campagne")

    if submitted:
        if not campaign_name.strip():
            st.error("Le nom de la campagne est obligatoire.")
        elif end_date < start_date:
            st.error("La date de fin doit etre posterieure a la date de debut.")
        else:
            try:
                campaign_id = create_campaign(
                    {
                        "campaign_name": campaign_name.strip(),
                        "campaign_type": campaign_type,
                        "platform": platform,
                        "description": description.strip() or None,
                        "influencer_handle": influencer_handle.strip() or None,
                        "influencer_tier": influencer_tier if influencer_tier != "none" else None,
                        "target_segment": target_segment.strip() or None,
                        "target_aspects": [item.strip() for item in target_aspects_raw.split(",") if item.strip()],
                        "target_regions": [
                            item.strip().lower() for item in target_regions_raw.split(",") if item.strip()
                        ],
                        "keywords": [item.strip().lower() for item in keywords_raw.split(",") if item.strip()],
                        "budget_dza": budget if budget > 0 else None,
                        "start_date": start_date.strftime("%Y-%m-%d"),
                        "end_date": end_date.strftime("%Y-%m-%d"),
                        "pre_window_days": int(pre_window),
                        "post_window_days": int(post_window),
                    }
                )
            except Exception as exc:
                st.error(f"Erreur lors de la creation : {exc}")
            else:
                if source_recommendation_id:
                    _clear_recommendation_query_param()
                st.success(f"Campagne creee avec l'ID : `{campaign_id}`")
                st.rerun()

with tab_impact:
    st.subheader("Analyse d'impact")

    if df.empty:
        st.warning("Donnees non disponibles. Lancez d'abord scripts/run_demo_05.py")
        st.stop()

    if not campaigns:
        st.info("Aucune campagne a analyser. Creez-en une d'abord.")
    else:
        camp_options = {campaign["campaign_name"]: campaign["campaign_id"] for campaign in campaigns}
        selected_name = st.selectbox("Selectionnez une campagne", list(camp_options.keys()))
        selected_id = camp_options[selected_name]

        if st.button("Calculer l'impact", type="primary"):
            try:
                with st.spinner("Calcul en cours..."):
                    result = compute_campaign_impact(selected_id, df)
            except Exception as exc:
                st.error(f"Erreur lors du calcul : {exc}")
            else:
                st.markdown(f"### Campagne : {result['campaign_name']}")

                if not result["is_reliable"]:
                    st.warning(result["reliability_note"])

                col_pre, col_act, col_post = st.columns(3)
                for col, phase_key, label in [
                    (col_pre, "pre", "Pre-campagne"),
                    (col_act, "active", "Active"),
                    (col_post, "post", "Post-campagne"),
                ]:
                    phase = result["phases"][phase_key]
                    with col:
                        st.metric(label, f"NSS {phase['nss']:.1f}" if phase["nss"] is not None else "NSS -")
                        st.caption(f"Volume : {phase['volume']} signaux")

                st.markdown("---")
                col_u1, col_u2 = st.columns(2)
                col_u1.metric(
                    "Uplift NSS (post - pre)",
                    f"{result['uplift_nss']:+.1f}" if result["uplift_nss"] is not None else "-",
                    delta_color="normal",
                )
                col_u2.metric(
                    "Uplift volume (%)",
                    f"{result['uplift_volume_pct']:+.1f}%" if result["uplift_volume_pct"] is not None else "-",
                )

                post_aspects = result["phases"]["post"]["aspect_breakdown"]
                if post_aspects:
                    st.markdown("#### NSS par aspect (post-campagne)")
                    aspect_df = pd.DataFrame(
                        [(aspect, nss) for aspect, nss in post_aspects.items()],
                        columns=["Aspect", "NSS"],
                    ).sort_values("NSS", ascending=True)
                    st.bar_chart(aspect_df.set_index("Aspect")["NSS"])

                snapshots_df = load_campaign_snapshots(selected_id)
                if not snapshots_df.empty:
                    st.markdown("#### Snapshots persistés")
                    st.dataframe(snapshots_df, use_container_width=True)

                links_df = load_campaign_signal_links(selected_id)
                if not links_df.empty:
                    st.markdown("#### Top signaux attribués")
                    st.dataframe(links_df, use_container_width=True)
