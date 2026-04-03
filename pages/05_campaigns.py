"""Streamlit page for Campaign Intelligence."""

from __future__ import annotations

import sqlite3
from datetime import date

import pandas as pd
import streamlit as st

from config import ANNOTATED_PARQUET_PATH, SQLITE_DB_PATH
from core.runtime.diagnostics import collect_runtime_diagnostics
from ui_helpers.annotated_data import load_annotated_parquet
from ui_helpers.campaigns_helpers import (
    build_campaign_comparison_bar_figure,
    build_campaign_comparison_frame,
    build_campaign_comparison_scatter_figure,
    build_campaign_daily_nss_figure,
    build_campaign_daily_nss_frame,
    build_campaign_heatmap_figure,
    build_campaign_phase_frames,
    build_campaign_signal_details_frame,
    build_campaign_summary_frame,
    build_campaign_timeline_figure,
    build_phase_absa_matrix,
)
from ui_helpers.runtime_panel import render_runtime_panel

st.set_page_config(page_title="Campagnes - RamyPulse", layout="wide")


@st.cache_data(ttl=300)
def load_data() -> pd.DataFrame:
    """Load annotated.parquet with normalized UI columns."""
    return load_annotated_parquet(ANNOTATED_PARQUET_PATH)


@st.cache_data(ttl=60, show_spinner=False)
def load_runtime_diagnostics() -> dict:
    """Load shared runtime diagnostics for UI visibility."""
    return collect_runtime_diagnostics()


def load_campaign_snapshots(campaign_id: str) -> pd.DataFrame:
    """Load persisted snapshots for one campaign."""
    with sqlite3.connect(SQLITE_DB_PATH) as connection:
        try:
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
        except Exception:
            return pd.DataFrame()


def load_all_campaign_snapshots() -> pd.DataFrame:
    """Load all campaign snapshots used by the global comparison view."""
    with sqlite3.connect(SQLITE_DB_PATH) as connection:
        try:
            return pd.read_sql_query(
                """
                SELECT campaign_id, phase, metric_date, nss_filtered, nss_baseline, nss_uplift,
                       volume_filtered, volume_baseline, volume_lift_pct, computed_at
                FROM campaign_metrics_snapshots
                ORDER BY computed_at DESC
                """,
                connection,
            )
        except Exception:
            return pd.DataFrame()


def load_campaign_signal_links(campaign_id: str, limit: int = 12) -> pd.DataFrame:
    """Load the latest batch of attributed signals for one campaign."""
    with sqlite3.connect(SQLITE_DB_PATH) as connection:
        try:
            return pd.read_sql_query(
                """
                SELECT phase, signal_id, attribution_score, attributed_at
                FROM campaign_signal_links
                WHERE campaign_id = ?
                  AND attributed_at = (
                    SELECT MAX(attributed_at)
                    FROM campaign_signal_links
                    WHERE campaign_id = ?
                  )
                ORDER BY attribution_score DESC, signal_id ASC
                LIMIT ?
                """,
                connection,
                params=(campaign_id, campaign_id, limit),
            )
        except Exception:
            return pd.DataFrame()


def _clear_recommendation_query_param() -> None:
    """Drop recommendation_id from query params if present."""
    if "recommendation_id" in st.query_params:
        del st.query_params["recommendation_id"]


def _campaign_options(campaigns: list[dict]) -> dict[str, str]:
    """Build selector labels for campaigns."""
    return {
        f"{campaign['campaign_name']} [{campaign.get('status') or 'planned'}]": campaign["campaign_id"]
        for campaign in campaigns
    }


def _default_campaign_index(campaigns: list[dict], preferred_id: str | None) -> int:
    """Return the default selection index for a campaign selector."""
    if not campaigns or not preferred_id:
        return 0
    for index, campaign in enumerate(campaigns):
        if campaign["campaign_id"] == preferred_id:
            return index
    return 0


def _format_metric(value: object, *, suffix: str = "", signed: bool = False) -> str:
    """Format a nullable numeric metric consistently."""
    if value is None or pd.isna(value):
        return "-"
    numeric = float(value)
    if signed:
        return f"{numeric:+.1f}{suffix}"
    return f"{numeric:.1f}{suffix}"


def _latest_snapshot_by_phase(snapshots_df: pd.DataFrame, phase: str) -> pd.Series | None:
    """Return the most recent snapshot for the requested phase."""
    if snapshots_df.empty:
        return None
    subset = snapshots_df[snapshots_df["phase"] == phase].copy()
    if subset.empty:
        return None
    subset["computed_at"] = pd.to_datetime(subset["computed_at"], errors="coerce")
    subset = subset.sort_values("computed_at", ascending=False)
    if subset.empty:
        return None
    return subset.iloc[0]


def _campaign_period_bounds(campaigns: list[dict]) -> tuple[date, date]:
    """Build a robust date range for the summary filters."""
    if not campaigns:
        today = pd.Timestamp.today().date()
        return today, today

    frame = pd.DataFrame(campaigns)
    start_series = pd.to_datetime(frame.get("start_date"), errors="coerce").dropna()
    end_series = pd.to_datetime(frame.get("end_date"), errors="coerce").dropna()
    if start_series.empty or end_series.empty:
        today = pd.Timestamp.today().date()
        return today, today
    return start_series.min().date(), end_series.max().date()


def _render_campaign_summary_table(campaigns: list[dict], snapshots_df: pd.DataFrame) -> pd.DataFrame:
    """Render the filterable summary table for campaigns."""
    status_options = ["Tous", "planned", "active", "completed", "cancelled"]
    platform_values = sorted({campaign.get("platform") or "" for campaign in campaigns if campaign.get("platform")})
    platform_options = ["Toutes", *platform_values]
    min_date, max_date = _campaign_period_bounds(campaigns)

    col_status, col_platform, col_period = st.columns([1, 1, 1.4])
    status_filter = col_status.selectbox("Statut", status_options, key="campaign_status_filter")
    platform_filter = col_platform.selectbox("Plateforme", platform_options, key="campaign_platform_filter")
    date_range = col_period.date_input(
        "Periode",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        key="campaign_period_filter",
    )

    if isinstance(date_range, tuple) and len(date_range) == 2:
        period_range = (pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1]))
    else:
        period_range = (pd.Timestamp(min_date), pd.Timestamp(max_date))

    summary_df = build_campaign_summary_frame(
        campaigns,
        snapshots_df,
        status_filter=status_filter,
        platform_filter=platform_filter,
        period_range=period_range,
    )

    if summary_df.empty:
        st.info("Aucune campagne ne correspond aux filtres selectionnes.")
        return summary_df

    display_df = summary_df.rename(
        columns={
            "campaign_name": "Campagne",
            "campaign_type": "Type",
            "platform": "Plateforme",
            "period": "Periode",
            "status": "Statut",
            "uplift_nss": "Uplift NSS",
            "uplift_volume_pct": "Volume lift %",
        }
    ).copy()
    display_df["Uplift NSS"] = display_df["Uplift NSS"].apply(lambda value: _format_metric(value, signed=True))
    display_df["Volume lift %"] = display_df["Volume lift %"].apply(
        lambda value: _format_metric(value, suffix="%", signed=True)
    )

    st.dataframe(display_df.drop(columns=["campaign_id"]), use_container_width=True, hide_index=True)
    return summary_df


def _render_campaign_management_panel(campaigns: list[dict], visible_campaigns: pd.DataFrame) -> None:
    """Render the management controls below the summary table."""
    selection_source = visible_campaigns["campaign_id"].tolist() if not visible_campaigns.empty else []
    if not selection_source:
        return

    campaigns_by_id = {campaign["campaign_id"]: campaign for campaign in campaigns}
    selection_labels = {
        campaign_id: campaigns_by_id[campaign_id]["campaign_name"]
        for campaign_id in selection_source
        if campaign_id in campaigns_by_id
    }
    selected_id = st.selectbox(
        "Selection de gestion",
        options=list(selection_labels.keys()),
        format_func=lambda campaign_id: selection_labels[campaign_id],
        key="campaign_management_selected",
    )
    st.session_state["campaign_focus_id"] = selected_id
    selected_campaign = campaigns_by_id[selected_id]

    st.caption(
        f"Type: {selected_campaign.get('campaign_type') or '-'} | "
        f"Plateforme: {selected_campaign.get('platform') or '-'} | "
        f"Periode: {selected_campaign.get('start_date') or '-'} -> {selected_campaign.get('end_date') or '-'}"
    )

    col_status, col_delete = st.columns([3, 1])
    with col_status:
        status_options = ["planned", "active", "completed", "cancelled"]
        next_status = st.selectbox(
            "Changer le statut",
            status_options,
            index=status_options.index(selected_campaign["status"]),
            key=f"campaign_status_{selected_id}",
        )
        if st.button("Mettre a jour le statut", key=f"campaign_update_{selected_id}"):
            try:
                update_campaign_status(selected_id, next_status)
            except Exception as exc:
                st.error(f"Erreur : {exc}")
            else:
                st.success("Statut mis a jour.")
                st.rerun()
    with col_delete:
        if st.button("Supprimer", key=f"campaign_delete_{selected_id}"):
            try:
                delete_campaign(selected_id)
            except Exception as exc:
                st.error(f"Erreur : {exc}")
            else:
                st.success("Campagne supprimee.")
                st.rerun()


df = load_data()

st.title("Campaign Intelligence")
st.caption("Creez, mesurez et comparez l'impact de vos campagnes marketing sur les metriques NSS.")
render_runtime_panel(load_runtime_diagnostics(), title="Diagnostic runtime")

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
        all_snapshots_df = load_all_campaign_snapshots()
        visible_campaigns = _render_campaign_summary_table(campaigns, all_snapshots_df)
        st.markdown("#### Gestion")
        _render_campaign_management_panel(campaigns, visible_campaigns)

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
                        "target_regions": [item.strip().lower() for item in target_regions_raw.split(",") if item.strip()],
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
                st.session_state["campaign_focus_id"] = campaign_id
                if source_recommendation_id:
                    _clear_recommendation_query_param()
                st.success(f"Campagne creee avec l'ID : `{campaign_id}`")
                st.rerun()

with tab_impact:
    st.subheader("Campaign Lab")

    if not campaigns:
        st.info("Aucune campagne a analyser. Creez-en une d'abord.")
    else:
        preferred_campaign_id = st.session_state.get("campaign_focus_id")
        campaign_labels = _campaign_options(campaigns)
        selected_label = st.selectbox(
            "Selectionnez une campagne",
            list(campaign_labels.keys()),
            index=_default_campaign_index(campaigns, preferred_campaign_id),
        )
        selected_id = campaign_labels[selected_label]
        st.session_state["campaign_focus_id"] = selected_id
        selected_campaign = next(campaign for campaign in campaigns if campaign["campaign_id"] == selected_id)

        st.caption(
            f"Type: {selected_campaign.get('campaign_type') or '-'} | "
            f"Plateforme: {selected_campaign.get('platform') or '-'} | "
            f"Periode: {selected_campaign.get('start_date') or '-'} -> {selected_campaign.get('end_date') or '-'}"
        )

        if st.button("Calculer / recalculer l'impact", type="primary", key="compute_campaign_impact"):
            if df.empty:
                st.warning("Donnees non disponibles. Le calcul d'impact ne peut pas etre lance.")
            else:
                try:
                    with st.spinner("Calcul en cours..."):
                        compute_campaign_impact(selected_id, df)
                except Exception as exc:
                    st.error(f"Erreur lors du calcul : {exc}")
                else:
                    st.success("Impact calcule et snapshots mis a jour.")

        st.markdown("#### Timeline campagne")
        st.plotly_chart(build_campaign_timeline_figure(selected_campaign), use_container_width=True)

        snapshots_df = load_campaign_snapshots(selected_id)
        all_snapshots_df = load_all_campaign_snapshots()
        links_df = load_campaign_signal_links(selected_id, limit=12)

        if df.empty:
            st.info(
                "Le dataset annote courant est indisponible. La timeline reste visible, "
                "mais les courbes, heatmaps et signaux attribues ne peuvent pas etre calcules."
            )
        else:
            phase_frames = build_campaign_phase_frames(df, selected_campaign)
            daily_frame = build_campaign_daily_nss_frame(df, selected_campaign)

            pre_snapshot = _latest_snapshot_by_phase(snapshots_df, "pre")
            post_snapshot = _latest_snapshot_by_phase(snapshots_df, "post")

            if snapshots_df.empty:
                st.info(
                    "Aucun snapshot persiste pour cette campagne. Lancez le calcul d'impact "
                    "pour alimenter les KPI et la comparaison multi-campagnes."
                )

            volume_total = sum(len(phase_frames.get(phase, pd.DataFrame())) for phase in ["pre", "active", "post"])
            kpi_columns = st.columns(5)
            kpi_columns[0].metric(
                "NSS pre-campagne",
                _format_metric(pre_snapshot["nss_filtered"] if pre_snapshot is not None else None),
            )
            kpi_columns[1].metric(
                "NSS post-campagne",
                _format_metric(post_snapshot["nss_filtered"] if post_snapshot is not None else None),
            )
            kpi_columns[2].metric(
                "Uplift NSS",
                _format_metric(post_snapshot["nss_uplift"] if post_snapshot is not None else None, signed=True),
            )
            kpi_columns[3].metric(
                "Volume lift %",
                _format_metric(
                    post_snapshot["volume_lift_pct"] if post_snapshot is not None else None,
                    suffix="%",
                    signed=True,
                ),
            )
            kpi_columns[4].metric("Volume total attribue", int(volume_total))

            st.markdown("#### Evolution NSS jour par jour")
            if daily_frame.empty:
                st.info("Aucune donnee filtree sur la fenetre de campagne selectionnee.")
            else:
                st.plotly_chart(build_campaign_daily_nss_figure(daily_frame, selected_campaign), use_container_width=True)

            st.markdown("#### Matrice ABSA avant / apres")
            pre_matrix = build_phase_absa_matrix(phase_frames.get("pre", pd.DataFrame()))
            post_matrix = build_phase_absa_matrix(phase_frames.get("post", pd.DataFrame()))
            if phase_frames.get("pre", pd.DataFrame()).empty and phase_frames.get("post", pd.DataFrame()).empty:
                st.info("Aucune donnee disponible sur les fenetres pre et post pour construire la heatmap.")
            else:
                st.plotly_chart(build_campaign_heatmap_figure(pre_matrix, post_matrix), use_container_width=True)

            st.markdown("#### Top signaux attribues")
            if links_df.empty:
                st.info("Aucun lien signal-campagne persiste. Lancez le calcul d'impact pour generer cette vue.")
            else:
                signal_details_df = build_campaign_signal_details_frame(links_df, df, selected_campaign)
                if signal_details_df.empty:
                    st.info("Aucun signal source correspondant n'a ete retrouve dans le dataset courant.")
                else:
                    signal_display_df = signal_details_df.copy()
                    signal_display_df["timestamp"] = signal_display_df["timestamp"].dt.strftime("%Y-%m-%d %H:%M")
                    signal_display_df = signal_display_df.rename(
                        columns={
                            "phase": "Phase",
                            "timestamp": "Timestamp",
                            "attribution_score": "Attribution",
                            "text_excerpt": "Extrait",
                            "source_url": "Source URL",
                            "signal_id": "Signal ID",
                        }
                    )
                    st.dataframe(signal_display_df, use_container_width=True, hide_index=True)

        st.markdown("#### Comparaison multi-campagnes")
        comparison_df = build_campaign_comparison_frame(campaigns, all_snapshots_df)
        if len(comparison_df) < 2:
            st.info("Calcul d'impact requis sur au moins deux campagnes pour activer la comparaison.")
        else:
            compare_col1, compare_col2 = st.columns(2)
            with compare_col1:
                st.plotly_chart(build_campaign_comparison_bar_figure(comparison_df), use_container_width=True)
            with compare_col2:
                st.plotly_chart(build_campaign_comparison_scatter_figure(comparison_df), use_container_width=True)

        if not snapshots_df.empty:
            with st.expander("Historique des snapshots persistés", expanded=False):
                snapshot_display_df = snapshots_df.copy()
                for column_name in ["nss_filtered", "nss_baseline", "nss_uplift", "volume_lift_pct"]:
                    if column_name in snapshot_display_df.columns:
                        snapshot_display_df[column_name] = snapshot_display_df[column_name].round(2)
                st.dataframe(snapshot_display_df, use_container_width=True, hide_index=True)
