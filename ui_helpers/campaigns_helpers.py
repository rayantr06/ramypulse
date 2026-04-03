"""Pure helpers for the Campaign Intelligence page.

The Streamlit page delegates dataframe preparation and Plotly figure assembly
to this module so the behavior can be tested without the UI runtime.
"""

from __future__ import annotations

import logging

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from config import ASPECT_LIST, SENTIMENT_LABELS
from core.campaigns.impact_calculator import _signal_id_for_row, filter_signals_for_campaign

logger = logging.getLogger(__name__)

_PHASE_ORDER = ["pre", "active", "post"]
_PHASE_COLORS = {
    "pre": "#E6F2FF",
    "active": "#FFE7B8",
    "post": "#E7F7ED",
}
_PHASE_LABELS = {
    "pre": "Pre-campagne",
    "active": "Campagne active",
    "post": "Post-campagne",
}


def _parse_bound(value: str, *, inclusive_end: bool) -> pd.Timestamp:
    """Convert a date or datetime string to a robust boundary."""
    parsed = pd.to_datetime(value)
    if "T" not in value and " " not in value:
        if inclusive_end:
            return parsed + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)
        return parsed
    return parsed


def _phase_for_timestamp(timestamp: pd.Timestamp, timeline_frame: pd.DataFrame) -> str | None:
    """Return the campaign phase that contains the timestamp."""
    moment = pd.Timestamp(timestamp)
    for row in timeline_frame.itertuples(index=False):
        if moment >= row.start and moment <= row.end:
            return str(row.phase)
    return None


def _compute_nss(dataframe: pd.DataFrame) -> float | None:
    """Compute a local NSS on a subset of signals."""
    if dataframe.empty or "sentiment_label" not in dataframe.columns:
        return None

    total = len(dataframe)
    if total == 0:
        return None

    positive_labels = {"tres_positif", "très_positif", "positif"}
    negative_labels = {"tres_negatif", "très_négatif", "négatif", "negatif"}
    positives = int(dataframe["sentiment_label"].isin(positive_labels).sum())
    negatives = int(dataframe["sentiment_label"].isin(negative_labels).sum())
    return round(((positives - negatives) / total) * 100.0, 2)


def _empty_daily_frame() -> pd.DataFrame:
    """Return an empty dataframe with the expected daily series schema."""
    return pd.DataFrame(columns=["date", "phase", "nss", "volume", "baseline_nss_pre"])


def build_campaign_timeline_frame(campaign: dict) -> pd.DataFrame:
    """Build the PRD pre/active/post windows for a campaign."""
    start_date = campaign.get("start_date")
    end_date = campaign.get("end_date")
    if not start_date or not end_date:
        return pd.DataFrame(columns=["phase", "label", "start", "end", "color", "track"])

    start_ts = _parse_bound(str(start_date), inclusive_end=False)
    end_ts = _parse_bound(str(end_date), inclusive_end=True)
    pre_window_days = int(campaign.get("pre_window_days") or 14)
    post_window_days = int(campaign.get("post_window_days") or 14)

    rows = [
        {
            "phase": "pre",
            "label": _PHASE_LABELS["pre"],
            "start": start_ts - pd.Timedelta(days=pre_window_days),
            "end": start_ts - pd.Timedelta(microseconds=1),
            "color": _PHASE_COLORS["pre"],
            "track": "Campagne",
        },
        {
            "phase": "active",
            "label": _PHASE_LABELS["active"],
            "start": start_ts,
            "end": end_ts,
            "color": _PHASE_COLORS["active"],
            "track": "Campagne",
        },
        {
            "phase": "post",
            "label": _PHASE_LABELS["post"],
            "start": end_ts + pd.Timedelta(microseconds=1),
            "end": end_ts + pd.Timedelta(days=post_window_days),
            "color": _PHASE_COLORS["post"],
            "track": "Campagne",
        },
    ]
    return pd.DataFrame(rows)


def build_campaign_timeline_figure(campaign: dict) -> go.Figure:
    """Build the campaign timeline Plotly figure."""
    timeline_frame = build_campaign_timeline_frame(campaign)
    if timeline_frame.empty:
        figure = go.Figure()
        figure.update_layout(height=180, margin=dict(l=20, r=20, t=20, b=20))
        return figure

    figure = px.timeline(
        timeline_frame,
        x_start="start",
        x_end="end",
        y="track",
        color="label",
        color_discrete_map={row["label"]: row["color"] for _, row in timeline_frame.iterrows()},
        hover_name="label",
        hover_data={"phase": True, "start": True, "end": True, "track": False},
    )
    figure.update_yaxes(visible=False)
    figure.update_layout(
        height=220,
        margin=dict(l=20, r=20, t=30, b=20),
        legend_title_text="Fenetre",
    )

    active_row = timeline_frame[timeline_frame["phase"] == "active"].iloc[0]
    figure.add_vline(x=active_row["start"], line_dash="dash", line_color="#B26A00")
    figure.add_vline(x=active_row["end"], line_dash="dash", line_color="#B26A00")
    return figure


def build_campaign_daily_nss_frame(dataframe: pd.DataFrame, campaign: dict) -> pd.DataFrame:
    """Build the complete daily NSS series on the pre/active/post window."""
    timeline_frame = build_campaign_timeline_frame(campaign)
    if timeline_frame.empty:
        return _empty_daily_frame()

    window_start = timeline_frame["start"].min()
    window_end = timeline_frame["end"].max()
    filtered = filter_signals_for_campaign(
        dataframe,
        campaign,
        window_start.isoformat(),
        window_end.isoformat(),
    ).copy()

    if "timestamp" in filtered.columns:
        filtered["timestamp"] = pd.to_datetime(filtered["timestamp"], errors="coerce")
        filtered = filtered[filtered["timestamp"].notna()]

    if not filtered.empty:
        filtered["phase"] = filtered["timestamp"].apply(lambda ts: _phase_for_timestamp(ts, timeline_frame))
        filtered["date"] = filtered["timestamp"].dt.normalize()

    pre_signals = filtered[filtered["phase"] == "pre"] if not filtered.empty else pd.DataFrame()
    baseline_nss = _compute_nss(pre_signals)

    rows: list[dict] = []
    for day in pd.date_range(window_start.normalize(), window_end.normalize(), freq="D"):
        phase = _phase_for_timestamp(day + pd.Timedelta(hours=12), timeline_frame)
        day_rows = filtered[filtered["date"] == day] if not filtered.empty else pd.DataFrame()
        rows.append(
            {
                "date": day,
                "phase": phase,
                "nss": _compute_nss(day_rows),
                "volume": int(len(day_rows)),
                "baseline_nss_pre": baseline_nss,
            }
        )

    return pd.DataFrame(rows)


def build_campaign_daily_nss_figure(daily_frame: pd.DataFrame, campaign: dict) -> go.Figure:
    """Build the daily NSS curve with daily volume bars."""
    figure = make_subplots(specs=[[{"secondary_y": True}]])
    if daily_frame.empty:
        figure.update_layout(height=360, margin=dict(l=20, r=20, t=30, b=20))
        return figure

    figure.add_bar(
        x=daily_frame["date"],
        y=daily_frame["volume"],
        name="Volume",
        marker_color="#D9E4F5",
        opacity=0.55,
        secondary_y=True,
        hovertemplate="Date: %{x|%Y-%m-%d}<br>Volume: %{y}<extra></extra>",
    )
    figure.add_scatter(
        x=daily_frame["date"],
        y=daily_frame["nss"],
        mode="lines+markers",
        name="NSS journalier",
        line=dict(color="#24577A", width=3),
        marker=dict(size=8),
        customdata=daily_frame[["phase", "volume"]],
        hovertemplate=(
            "Date: %{x|%Y-%m-%d}<br>"
            "NSS: %{y:+.2f}<br>"
            "Phase: %{customdata[0]}<br>"
            "Volume: %{customdata[1]}<extra></extra>"
        ),
        secondary_y=False,
    )

    baseline = daily_frame["baseline_nss_pre"].dropna()
    if not baseline.empty:
        figure.add_hline(
            y=float(baseline.iloc[0]),
            line_dash="dot",
            line_color="#4F6D7A",
            annotation_text="Baseline pre-campagne",
            annotation_position="top left",
        )

    for phase in _PHASE_ORDER:
        phase_days = daily_frame[daily_frame["phase"] == phase]
        if phase_days.empty:
            continue
        figure.add_vrect(
            x0=phase_days["date"].min(),
            x1=phase_days["date"].max() + pd.Timedelta(days=1),
            fillcolor=_PHASE_COLORS[phase],
            opacity=0.22,
            line_width=0,
            annotation_text=_PHASE_LABELS[phase],
            annotation_position="top left",
        )

    figure.update_yaxes(title_text="NSS", range=[-100, 100], secondary_y=False)
    figure.update_yaxes(title_text="Volume", secondary_y=True)
    figure.update_layout(
        height=420,
        margin=dict(l=20, r=20, t=30, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return figure


def build_phase_absa_matrix(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Build a fixed 5x5 ABSA matrix."""
    if dataframe.empty or "aspect" not in dataframe.columns or "sentiment_label" not in dataframe.columns:
        return pd.DataFrame(0, index=ASPECT_LIST, columns=SENTIMENT_LABELS)

    matrix = pd.crosstab(dataframe["aspect"], dataframe["sentiment_label"])
    return matrix.reindex(index=ASPECT_LIST, columns=SENTIMENT_LABELS, fill_value=0)


def build_campaign_heatmap_figure(pre_matrix: pd.DataFrame, post_matrix: pd.DataFrame) -> go.Figure:
    """Build the double ABSA heatmap figure."""
    zmax = int(max(pre_matrix.to_numpy().max(initial=0), post_matrix.to_numpy().max(initial=0), 1))
    figure = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=("Pre-campagne", "Post-campagne"),
        horizontal_spacing=0.12,
    )
    for column_index, (title, matrix) in enumerate(
        [("Pre-campagne", pre_matrix), ("Post-campagne", post_matrix)],
        start=1,
    ):
        figure.add_trace(
            go.Heatmap(
                z=matrix.values,
                x=matrix.columns.tolist(),
                y=matrix.index.tolist(),
                zmin=0,
                zmax=zmax,
                colorscale="RdYlGn",
                text=matrix.values,
                texttemplate="%{text}",
                colorbar=dict(title="Count") if column_index == 2 else None,
                hovertemplate=(
                    f"Phase: {title}<br>Aspect: %{{y}}<br>"
                    "Sentiment: %{x}<br>Count: %{z}<extra></extra>"
                ),
                showscale=column_index == 2,
            ),
            row=1,
            col=column_index,
        )
    figure.update_layout(height=460, margin=dict(l=20, r=20, t=50, b=20))
    return figure


def build_campaign_phase_frames(dataframe: pd.DataFrame, campaign: dict) -> dict[str, pd.DataFrame]:
    """Split campaign signals into three phase dataframes."""
    timeline_frame = build_campaign_timeline_frame(campaign)
    if timeline_frame.empty:
        return {phase: pd.DataFrame() for phase in _PHASE_ORDER}

    window_start = timeline_frame["start"].min()
    window_end = timeline_frame["end"].max()
    filtered = filter_signals_for_campaign(
        dataframe,
        campaign,
        window_start.isoformat(),
        window_end.isoformat(),
    ).copy()
    if "timestamp" in filtered.columns:
        filtered["timestamp"] = pd.to_datetime(filtered["timestamp"], errors="coerce")
        filtered = filtered[filtered["timestamp"].notna()]
    if filtered.empty:
        return {phase: pd.DataFrame() for phase in _PHASE_ORDER}

    filtered["phase"] = filtered["timestamp"].apply(lambda ts: _phase_for_timestamp(ts, timeline_frame))
    return {phase: filtered[filtered["phase"] == phase].copy() for phase in _PHASE_ORDER}


def build_campaign_signal_details_frame(
    links_df: pd.DataFrame,
    source_df: pd.DataFrame,
    campaign: dict,
) -> pd.DataFrame:
    """Enrich campaign signal links with source metadata from the dataset."""
    if links_df.empty:
        return pd.DataFrame(
            columns=["phase", "timestamp", "attribution_score", "text_excerpt", "source_url", "signal_id"]
        )

    phase_frames = build_campaign_phase_frames(source_df, campaign)
    catalog_rows: list[dict] = []
    for phase, phase_df in phase_frames.items():
        if phase_df.empty:
            continue
        for _, row in phase_df.iterrows():
            text_value = row.get("text_original") or row.get("text") or ""
            catalog_rows.append(
                {
                    "phase": phase,
                    "signal_id": _signal_id_for_row(row, phase),
                    "timestamp": pd.to_datetime(row.get("timestamp"), errors="coerce"),
                    "text_excerpt": str(text_value)[:180],
                    "source_url": row.get("source_url") or "",
                }
            )

    catalog_df = pd.DataFrame(catalog_rows)
    enriched = links_df.copy()
    if not catalog_df.empty:
        enriched = enriched.merge(catalog_df, on=["phase", "signal_id"], how="left")

    for column_name, default_value in [
        ("timestamp", pd.NaT),
        ("text_excerpt", ""),
        ("source_url", ""),
    ]:
        if column_name not in enriched.columns:
            enriched[column_name] = default_value

    enriched["timestamp"] = pd.to_datetime(enriched["timestamp"], errors="coerce")
    enriched = enriched.sort_values(
        by=["attribution_score", "timestamp"],
        ascending=[False, False],
        na_position="last",
    )

    return enriched[
        ["phase", "timestamp", "attribution_score", "text_excerpt", "source_url", "signal_id"]
    ].reset_index(drop=True)


def build_campaign_comparison_frame(campaigns: list[dict], snapshots_df: pd.DataFrame) -> pd.DataFrame:
    """Build the comparison base using the latest post snapshot per campaign."""
    columns = ["campaign_id", "campaign_name", "uplift_nss", "uplift_volume_pct", "computed_at"]
    if snapshots_df.empty:
        return pd.DataFrame(columns=columns)

    snapshot_frame = snapshots_df.copy()
    snapshot_frame = snapshot_frame[snapshot_frame["phase"] == "post"]
    if snapshot_frame.empty:
        return pd.DataFrame(columns=columns)

    snapshot_frame["computed_at"] = pd.to_datetime(snapshot_frame["computed_at"], errors="coerce")
    snapshot_frame = snapshot_frame.sort_values(["campaign_id", "computed_at"], ascending=[True, False])
    latest_post = snapshot_frame.drop_duplicates(subset=["campaign_id"], keep="first")

    campaigns_frame = pd.DataFrame(campaigns)
    if campaigns_frame.empty:
        return pd.DataFrame(columns=columns)

    comparison = latest_post.merge(
        campaigns_frame[["campaign_id", "campaign_name"]],
        on="campaign_id",
        how="inner",
    )
    comparison = comparison.rename(
        columns={
            "nss_uplift": "uplift_nss",
            "volume_lift_pct": "uplift_volume_pct",
        }
    )
    comparison = comparison[
        ["campaign_id", "campaign_name", "uplift_nss", "uplift_volume_pct", "computed_at"]
    ].sort_values(
        by=["uplift_nss", "campaign_name"],
        ascending=[False, True],
        na_position="last",
    )
    return comparison.reset_index(drop=True)


def build_campaign_comparison_bar_figure(comparison_df: pd.DataFrame) -> go.Figure:
    """Build the uplift NSS bar chart."""
    figure = px.bar(
        comparison_df,
        x="campaign_name",
        y="uplift_nss",
        color="uplift_nss",
        color_continuous_scale="RdYlGn",
        labels={"campaign_name": "Campagne", "uplift_nss": "Uplift NSS"},
    )
    figure.update_layout(height=360, margin=dict(l=20, r=20, t=30, b=20), coloraxis_showscale=False)
    return figure


def build_campaign_comparison_scatter_figure(comparison_df: pd.DataFrame) -> go.Figure:
    """Build the uplift NSS vs volume lift scatter plot."""
    figure = px.scatter(
        comparison_df,
        x="uplift_volume_pct",
        y="uplift_nss",
        text="campaign_name",
        labels={"uplift_volume_pct": "Volume lift %", "uplift_nss": "Uplift NSS"},
    )
    figure.update_traces(textposition="top center", marker=dict(size=12, color="#24577A"))
    figure.update_layout(height=360, margin=dict(l=20, r=20, t=30, b=20))
    return figure


def build_campaign_summary_frame(
    campaigns: list[dict],
    snapshots_df: pd.DataFrame,
    *,
    status_filter: str = "Tous",
    platform_filter: str = "Toutes",
    period_range: tuple[pd.Timestamp, pd.Timestamp] | None = None,
) -> pd.DataFrame:
    """Build the filterable campaign summary table."""
    frame = pd.DataFrame(campaigns)
    if frame.empty:
        return pd.DataFrame(
            columns=[
                "campaign_id",
                "campaign_name",
                "campaign_type",
                "platform",
                "period",
                "status",
                "uplift_nss",
                "uplift_volume_pct",
            ]
        )

    if status_filter != "Tous":
        frame = frame[frame["status"] == status_filter]
    if platform_filter != "Toutes":
        frame = frame[frame["platform"] == platform_filter]

    if period_range is not None and {"start_date", "end_date"}.issubset(frame.columns):
        range_start, range_end = period_range
        start_series = pd.to_datetime(frame["start_date"], errors="coerce")
        end_series = pd.to_datetime(frame["end_date"], errors="coerce")
        overlap_mask = start_series.le(range_end) & end_series.ge(range_start)
        frame = frame[overlap_mask.fillna(False)]

    comparison = build_campaign_comparison_frame(campaigns, snapshots_df)
    if not comparison.empty:
        frame = frame.merge(
            comparison[["campaign_id", "uplift_nss", "uplift_volume_pct"]],
            on="campaign_id",
            how="left",
        )
    else:
        frame["uplift_nss"] = pd.NA
        frame["uplift_volume_pct"] = pd.NA

    frame["period"] = frame.apply(
        lambda row: f"{row.get('start_date') or '-'} -> {row.get('end_date') or '-'}",
        axis=1,
    )

    return frame[
        [
            "campaign_id",
            "campaign_name",
            "campaign_type",
            "platform",
            "period",
            "status",
            "uplift_nss",
            "uplift_volume_pct",
        ]
    ].sort_values(by=["campaign_name"], ascending=True, na_position="last").reset_index(drop=True)
