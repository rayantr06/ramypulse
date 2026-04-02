"""Page Streamlit — Campaign Intelligence.

Permet de créer, lister et analyser l'impact des campagnes marketing.
Conforme au template Section 6 de INTERFACES.md.
"""

from __future__ import annotations

import sqlite3

import pandas as pd
import streamlit as st

from config import ANNOTATED_PARQUET_PATH, DEFAULT_CLIENT_ID, SQLITE_DB_PATH

st.set_page_config(page_title="Campagnes — RamyPulse", layout="wide")


# ─── Chargement des données ───────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_data() -> pd.DataFrame:
    """Charge annotated.parquet. Retourne DataFrame vide si fichier absent."""
    try:
        df = pd.read_parquet(ANNOTATED_PARQUET_PATH)
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df["wilaya"] = df["wilaya"].fillna("").str.lower().str.strip() if "wilaya" in df.columns else ""
        df["aspect"] = df["aspect"].fillna("") if "aspect" in df.columns else ""
        return df
    except FileNotFoundError:
        return pd.DataFrame()


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


df = load_data()

# ─── Header ──────────────────────────────────────────────────────────────────
st.title("🎯 Campaign Intelligence")
st.caption("Créez et mesurez l'impact de vos campagnes marketing sur les métriques NSS.")

# ─── Chargement des campagnes existantes ─────────────────────────────────────
try:
    from core.campaigns.campaign_manager import (
        create_campaign,
        delete_campaign,
        get_campaign,
        list_campaigns,
        update_campaign_status,
    )
    from core.campaigns.impact_calculator import compute_campaign_impact

    campaigns = list_campaigns(limit=100)
except Exception as exc:
    st.error(f"Erreur SQLite : {exc}")
    st.stop()

# ─── Tabs ─────────────────────────────────────────────────────────────────────
tab_list, tab_create, tab_impact = st.tabs(["📋 Campagnes", "➕ Nouvelle campagne", "📊 Impact"])

# ─── Tab 1 : Liste des campagnes ─────────────────────────────────────────────
with tab_list:
    st.subheader("Campagnes enregistrées")

    if not campaigns:
        st.info("Aucune campagne enregistrée. Créez-en une dans l'onglet **Nouvelle campagne**.")
    else:
        status_filter = st.selectbox(
            "Filtrer par statut",
            ["Tous", "planned", "active", "completed", "cancelled"],
            key="status_filter",
        )
        filtered = [c for c in campaigns if status_filter == "Tous" or c["status"] == status_filter]

        for camp in filtered:
            with st.expander(f"**{camp['campaign_name']}** — {camp['status'].upper()}", expanded=False):
                col1, col2, col3 = st.columns(3)
                col1.metric("Type", camp.get("campaign_type") or "—")
                col2.metric("Plateforme", camp.get("platform") or "—")
                col3.metric("Budget (DZA)", f"{camp.get('budget_dza') or 0:,}")

                col4, col5 = st.columns(2)
                col4.write(f"**Début :** {camp.get('start_date') or '—'}")
                col5.write(f"**Fin :** {camp.get('end_date') or '—'}")

                if camp.get("target_aspects"):
                    st.write(f"**Aspects ciblés :** {', '.join(camp['target_aspects'])}")
                if camp.get("target_regions"):
                    st.write(f"**Régions :** {', '.join(camp['target_regions'])}")
                if camp.get("keywords"):
                    st.write(f"**Mots-clés :** {', '.join(camp['keywords'])}")

                col_status, col_del = st.columns([3, 1])
                with col_status:
                    new_status = st.selectbox(
                        "Changer statut",
                        ["planned", "active", "completed", "cancelled"],
                        index=["planned", "active", "completed", "cancelled"].index(camp["status"]),
                        key=f"status_{camp['campaign_id']}",
                    )
                    if st.button("Mettre à jour", key=f"upd_{camp['campaign_id']}"):
                        try:
                            update_campaign_status(camp["campaign_id"], new_status)
                            st.success("Statut mis à jour.")
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Erreur : {exc}")
                with col_del:
                    if st.button("🗑️ Supprimer", key=f"del_{camp['campaign_id']}"):
                        try:
                            delete_campaign(camp["campaign_id"])
                            st.success("Campagne supprimée.")
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Erreur : {exc}")

# ─── Tab 2 : Création d'une nouvelle campagne ─────────────────────────────────
with tab_create:
    st.subheader("Nouvelle campagne")

    with st.form("form_create_campaign"):
        col1, col2 = st.columns(2)
        campaign_name = col1.text_input("Nom de la campagne *", placeholder="Ex : Influenceur Oran Ramadan 2026")
        campaign_type = col2.selectbox(
            "Type",
            ["influencer", "paid_ad", "sponsoring", "launch", "promotion", "organic"],
        )

        col3, col4 = st.columns(2)
        platform = col3.selectbox(
            "Plateforme",
            ["instagram", "facebook", "youtube", "tiktok", "offline", "multi_platform"],
        )
        influencer_tier = col4.selectbox(
            "Tier influenceur",
            ["none", "nano", "micro", "macro", "mega"],
        )

        influencer_handle = st.text_input("Handle influenceur", placeholder="@nomhandle")
        description = st.text_area("Description", height=80)

        col5, col6 = st.columns(2)
        start_date = col5.date_input("Date de début")
        end_date = col6.date_input("Date de fin")

        col7, col8 = st.columns(2)
        pre_window = col7.number_input("Fenêtre pré-campagne (jours)", min_value=1, max_value=90, value=14)
        post_window = col8.number_input("Fenêtre post-campagne (jours)", min_value=1, max_value=90, value=14)

        budget = st.number_input("Budget (DZA)", min_value=0, value=0, step=10000)

        target_aspects_raw = st.text_input(
            "Aspects ciblés (séparés par virgule)",
            placeholder="emballage, goût",
        )
        target_regions_raw = st.text_input(
            "Régions ciblées (séparés par virgule)",
            placeholder="oran, alger",
        )
        keywords_raw = st.text_input(
            "Mots-clés (séparés par virgule)",
            placeholder="ramy, jus, bouteille",
        )

        submitted = st.form_submit_button("✅ Créer la campagne")

    if submitted:
        if not campaign_name.strip():
            st.error("Le nom de la campagne est obligatoire.")
        elif end_date < start_date:
            st.error("La date de fin doit être postérieure à la date de début.")
        else:
            try:
                cid = create_campaign({
                    "campaign_name": campaign_name.strip(),
                    "campaign_type": campaign_type,
                    "platform": platform,
                    "description": description.strip() or None,
                    "influencer_handle": influencer_handle.strip() or None,
                    "influencer_tier": influencer_tier if influencer_tier != "none" else None,
                    "target_aspects": [a.strip() for a in target_aspects_raw.split(",") if a.strip()],
                    "target_regions": [r.strip().lower() for r in target_regions_raw.split(",") if r.strip()],
                    "keywords": [k.strip().lower() for k in keywords_raw.split(",") if k.strip()],
                    "budget_dza": budget if budget > 0 else None,
                    "start_date": start_date.strftime("%Y-%m-%d"),
                    "end_date": end_date.strftime("%Y-%m-%d"),
                    "pre_window_days": int(pre_window),
                    "post_window_days": int(post_window),
                })
                st.success(f"Campagne créée avec l'ID : `{cid}`")
                st.rerun()
            except Exception as exc:
                st.error(f"Erreur lors de la création : {exc}")

# ─── Tab 3 : Analyse d'impact ─────────────────────────────────────────────────
with tab_impact:
    st.subheader("Analyse d'impact")

    if df.empty:
        st.warning("⚠️ Données non disponibles. Lancez d'abord scripts/run_demo_05.py")
        st.stop()

    if not campaigns:
        st.info("Aucune campagne à analyser. Créez-en une d'abord.")
    else:
        camp_options = {c["campaign_name"]: c["campaign_id"] for c in campaigns}
        selected_name = st.selectbox("Sélectionnez une campagne", list(camp_options.keys()))
        selected_id = camp_options[selected_name]

        if st.button("Calculer l'impact", type="primary"):
            try:
                with st.spinner("Calcul en cours…"):
                    result = compute_campaign_impact(selected_id, df)

                st.markdown(f"### Campagne : {result['campaign_name']}")

                # Fiabilité
                if not result["is_reliable"]:
                    st.warning(f"⚠️ {result['reliability_note']}")

                # Métriques des 3 phases
                col_pre, col_act, col_post = st.columns(3)
                for col, phase_key, label in [
                    (col_pre, "pre", "Pré-campagne"),
                    (col_act, "active", "Active"),
                    (col_post, "post", "Post-campagne"),
                ]:
                    phase = result["phases"][phase_key]
                    with col:
                        st.metric(label, f"NSS {phase['nss']:.1f}" if phase["nss"] is not None else "NSS —")
                        st.caption(f"Volume : {phase['volume']} signaux")

                # Uplift
                st.markdown("---")
                col_u1, col_u2 = st.columns(2)
                col_u1.metric(
                    "Uplift NSS (post − pré)",
                    f"{result['uplift_nss']:+.1f}" if result["uplift_nss"] is not None else "—",
                    delta_color="normal",
                )
                col_u2.metric(
                    "Uplift volume (%)",
                    f"{result['uplift_volume_pct']:+.1f}%" if result["uplift_volume_pct"] is not None else "—",
                )

                # Détail aspect breakdown post-campagne
                post_aspects = result["phases"]["post"]["aspect_breakdown"]
                if post_aspects:
                    st.markdown("#### NSS par aspect (post-campagne)")
                    aspect_df = pd.DataFrame(
                        [(asp, nss) for asp, nss in post_aspects.items()],
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

            except Exception as exc:
                st.error(f"Erreur lors du calcul : {exc}")
