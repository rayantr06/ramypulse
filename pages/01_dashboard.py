"""Dashboard principal ABSA + NSS pour RamyPulse."""

import logging
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import ASPECT_LIST, CHANNELS, DATA_DIR, SENTIMENT_LABELS
from core.analysis.nss_calculator import calculate_nss
from ui_helpers.annotated_data import load_annotated_parquet, normalize_annotated_dataframe
from ui_helpers.phase1_dashboard_helpers import (
    apply_dataframe_filters,
    build_available_filters,
    default_date_range,
    format_missing_dimensions,
    missing_filter_columns,
)
from ui_helpers.whatif_helpers import build_mock_df

logger = logging.getLogger(__name__)

_PARQUET_PATH = DATA_DIR / "processed" / "annotated.parquet"
_SENTIMENT_ORDER = SENTIMENT_LABELS
_HEATMAP_COLORS = "RdYlGn"

_NSS_COLORS = {
    "excellent": "#2E7D32",
    "bon": "#66BB6A",
    "moyen": "#FFA726",
    "problematique": "#E53935",
}


def _nss_color(nss: float) -> str:
    """Retourne la couleur CSS adaptee au score NSS."""
    if nss > 50:
        return _NSS_COLORS["excellent"]
    if nss > 20:
        return _NSS_COLORS["bon"]
    if nss >= 0:
        return _NSS_COLORS["moyen"]
    return _NSS_COLORS["problematique"]


def _nss_arrow(nss: float) -> str:
    """Retourne la fleche directionnelle pour le NSS."""
    if nss > 0:
        return "▲"
    if nss < 0:
        return "▼"
    return "●"


@st.cache_data(ttl=300)
def _load_data() -> pd.DataFrame:
    """Charge le dataset annote depuis le Parquet ou fallback demo."""
    if _PARQUET_PATH.exists():
        return load_annotated_parquet(_PARQUET_PATH)
    logger.warning("Aucune donnee trouvee - mode demo avec donnees synthetiques.")
    return normalize_annotated_dataframe(build_mock_df(n=500))


def _build_filters(df: pd.DataFrame) -> pd.DataFrame:
    """Construit les filtres sidebar et retourne le DataFrame filtre."""
    st.sidebar.header("Filtres")

    available_filters = build_available_filters(
        df,
        ["channel", "aspect", "product", "wilaya"],
    )
    missing_dimensions = missing_filter_columns(df, ["product", "wilaya"])
    if missing_dimensions:
        st.sidebar.caption(format_missing_dimensions(missing_dimensions))

    min_date, max_date = default_date_range(df)
    date_range = st.sidebar.date_input(
        "Periode",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

    selected_channels = st.sidebar.multiselect(
        "Canaux",
        options=available_filters["channel"] if not df.empty else CHANNELS,
        default=None,
        placeholder="Tous les canaux",
    )
    selected_aspects = st.sidebar.multiselect(
        "Aspects",
        options=available_filters["aspect"] if not df.empty else ASPECT_LIST,
        default=None,
        placeholder="Tous les aspects",
    )

    selected_products: list[str] = []
    if "product" in df.columns:
        selected_products = st.sidebar.multiselect(
            "Produits",
            options=available_filters["product"],
            default=None,
            placeholder="Tous les produits",
        )

    selected_wilayas: list[str] = []
    if "wilaya" in df.columns:
        selected_wilayas = st.sidebar.multiselect(
            "Wilayas",
            options=available_filters["wilaya"],
            default=None,
            placeholder="Toutes les wilayas",
        )

    return apply_dataframe_filters(
        df,
        {
            "date_range": date_range,
            "channel": selected_channels,
            "aspect": selected_aspects,
            "product": selected_products,
            "wilaya": selected_wilayas,
        },
    )


def _render_kpis(nss_result: dict, df: pd.DataFrame) -> None:
    """Affiche la rangee de KPI."""
    nss = nss_result["nss_global"]
    volume = nss_result["volume_total"]
    nb_channels = df["channel"].nunique() if not df.empty else 0
    nb_products = df["product"].nunique() if "product" in df.columns and not df.empty else 0
    nb_wilayas = df["wilaya"].nunique() if "wilaya" in df.columns and not df.empty else 0

    if not df.empty and df["timestamp"].notna().any():
        min_d = df["timestamp"].min().strftime("%d/%m/%y")
        max_d = df["timestamp"].max().strftime("%d/%m/%y")
        period = f"{min_d} - {max_d}"
    else:
        period = "-"

    columns = st.columns(6)
    with columns[0]:
        color = _nss_color(nss)
        arrow = _nss_arrow(nss)
        st.markdown(
            f"""<div style="background:{color};color:white;padding:20px;
            border-radius:10px;text-align:center;">
            <h3 style="margin:0;color:white;">NSS Global</h3>
            <h1 style="margin:5px 0;color:white;">{arrow} {nss:+.1f}</h1>
            </div>""",
            unsafe_allow_html=True,
        )
    with columns[1]:
        st.metric("Volume total", f"{volume:,}".replace(",", " "))
    with columns[2]:
        st.metric("Canaux actifs", nb_channels)
    with columns[3]:
        st.metric("Produits visibles", nb_products)
    with columns[4]:
        st.metric("Wilayas visibles", nb_wilayas)
    with columns[5]:
        st.metric("Periode", period)


def _render_heatmap(df: pd.DataFrame) -> None:
    """Affiche la matrice ABSA 5 aspects x 5 sentiments."""
    st.subheader("Matrice ABSA - Aspects x Sentiments")

    if df.empty:
        st.info("Aucune donnee pour la matrice.")
        return

    crosstab = pd.crosstab(df["aspect"], df["sentiment_label"])
    for asp in ASPECT_LIST:
        if asp not in crosstab.index:
            crosstab.loc[asp] = 0
    for sent in _SENTIMENT_ORDER:
        if sent not in crosstab.columns:
            crosstab[sent] = 0

    crosstab = crosstab.reindex(index=ASPECT_LIST, columns=_SENTIMENT_ORDER, fill_value=0)

    fig = go.Figure(
        data=go.Heatmap(
            z=crosstab.values,
            x=crosstab.columns.tolist(),
            y=crosstab.index.tolist(),
            colorscale=_HEATMAP_COLORS,
            texttemplate="%{z}",
            hovertemplate="Aspect: %{y}<br>Sentiment: %{x}<br>Count: %{z}<extra></extra>",
        )
    )
    fig.update_layout(
        height=400,
        margin=dict(l=20, r=20, t=30, b=20),
        xaxis_title="Sentiment",
        yaxis_title="Aspect",
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_nss_by_channel(nss_result: dict) -> None:
    """Affiche le NSS par canal."""
    st.subheader("NSS par canal")

    nss_by_channel = nss_result["nss_by_channel"]
    if not nss_by_channel:
        st.info("Aucune donnee par canal.")
        return

    frame = pd.DataFrame(
        [{"canal": channel, "nss": score} for channel, score in nss_by_channel.items()]
    ).sort_values("nss")

    fig = go.Figure(
        go.Bar(
            x=frame["nss"],
            y=frame["canal"],
            orientation="h",
            marker_color=[_nss_color(value) for value in frame["nss"]],
            text=[f"{value:+.1f}" for value in frame["nss"]],
            textposition="auto",
        )
    )
    fig.update_layout(
        height=300,
        margin=dict(l=20, r=20, t=10, b=20),
        xaxis_title="NSS",
        yaxis_title="",
        xaxis=dict(range=[-100, 100]),
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_nss_by_business_dimension(df: pd.DataFrame, column: str, title: str) -> None:
    """Affiche un top simple par dimension metier si la colonne existe."""
    if column not in df.columns:
        return

    grouped = (
        df.dropna(subset=[column])
        .groupby(column)
        .apply(lambda chunk: calculate_nss(chunk)["nss_global"])
        .reset_index(name="nss")
        .sort_values("nss", ascending=False)
        .head(10)
    )

    if grouped.empty:
        return

    st.subheader(title)
    fig = px.bar(
        grouped,
        x=column,
        y="nss",
        color="nss",
        color_continuous_scale="RdYlGn",
        range_color=[-100, 100],
    )
    fig.update_layout(height=320, margin=dict(l=20, r=20, t=10, b=20))
    st.plotly_chart(fig, use_container_width=True)


def _render_trends(nss_result: dict) -> None:
    """Affiche la tendance NSS hebdomadaire."""
    st.subheader("Tendance NSS hebdomadaire")

    trends = nss_result["trends"]
    if trends.empty:
        st.info("Pas assez de donnees pour les tendances.")
        return

    fig = px.line(
        trends,
        x="week_start",
        y="nss",
        markers=True,
        labels={"week_start": "Semaine", "nss": "NSS"},
    )
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
    fig.update_layout(
        height=350,
        margin=dict(l=20, r=20, t=10, b=20),
        yaxis=dict(range=[-100, 100]),
    )
    st.plotly_chart(fig, use_container_width=True)


def main() -> None:
    """Rendu de la page Dashboard."""
    st.title("Dashboard ABSA + NSS")

    raw = _load_data()
    if not _PARQUET_PATH.exists():
        st.info(
            "Mode demo - donnees synthetiques. "
            "Placez un fichier annote dans `data/processed/` pour les vraies donnees."
        )

    filtered = _build_filters(raw)
    nss_result = calculate_nss(filtered)

    _render_kpis(nss_result, filtered)
    st.divider()

    left, right = st.columns([3, 2])
    with left:
        _render_heatmap(filtered)
    with right:
        _render_nss_by_channel(nss_result)

    st.divider()
    business_left, business_right = st.columns(2)
    with business_left:
        _render_nss_by_business_dimension(filtered, "product", "NSS par produit")
    with business_right:
        _render_nss_by_business_dimension(filtered, "wilaya", "NSS par wilaya")

    st.divider()
    _render_trends(nss_result)


main()
