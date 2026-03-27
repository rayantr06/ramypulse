"""Dashboard principal ABSA + NSS pour RamyPulse."""

import logging
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Ajouter la racine du projet au path pour les imports locaux
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import ASPECT_LIST, CHANNELS, DATA_DIR, SENTIMENT_LABELS
from core.analysis.nss_calculator import calculate_nss
from pages.whatif_helpers import build_mock_df

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes visuelles
# ---------------------------------------------------------------------------

_PARQUET_PATH = DATA_DIR / "processed" / "annotated.parquet"

_SENTIMENT_ORDER = SENTIMENT_LABELS

_HEATMAP_COLORS = "RdYlGn"

_NSS_COLORS = {
    "excellent": "#2E7D32",   # > 50
    "bon": "#66BB6A",         # 20-50
    "moyen": "#FFA726",       # 0-20
    "problematique": "#E53935",  # < 0
}


def _nss_color(nss: float) -> str:
    """Retourne la couleur CSS adaptée au score NSS."""
    if nss > 50:
        return _NSS_COLORS["excellent"]
    if nss > 20:
        return _NSS_COLORS["bon"]
    if nss >= 0:
        return _NSS_COLORS["moyen"]
    return _NSS_COLORS["problematique"]


def _nss_arrow(nss: float) -> str:
    """Retourne la flèche directionnelle pour le NSS."""
    if nss > 0:
        return "▲"
    if nss < 0:
        return "▼"
    return "●"


# ---------------------------------------------------------------------------
# Chargement des données
# ---------------------------------------------------------------------------

@st.cache_data(ttl=300)
def _load_data() -> pd.DataFrame:
    """Charge le dataset annoté depuis le Parquet ou fallback démo."""
    if _PARQUET_PATH.exists():
        df = pd.read_parquet(_PARQUET_PATH)
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        return df
    logger.warning("Aucune donnée trouvée — mode démo avec données synthétiques.")
    df = build_mock_df(n=500)
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    return df


# ---------------------------------------------------------------------------
# Filtres sidebar
# ---------------------------------------------------------------------------

def _build_filters(df: pd.DataFrame) -> pd.DataFrame:
    """Construit les filtres dans la sidebar et retourne le DataFrame filtré."""
    st.sidebar.header("Filtres")

    # Période
    if not df.empty and df["timestamp"].notna().any():
        min_date = df["timestamp"].min().date()
        max_date = df["timestamp"].max().date()
    else:
        min_date = pd.Timestamp.today().date()
        max_date = min_date

    date_range = st.sidebar.date_input(
        "Période",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

    # Canaux
    selected_channels = st.sidebar.multiselect(
        "Canaux",
        options=sorted(df["channel"].dropna().unique()) if not df.empty else CHANNELS,
        default=None,
        placeholder="Tous les canaux",
    )

    # Aspects
    selected_aspects = st.sidebar.multiselect(
        "Aspects",
        options=sorted(df["aspect"].dropna().unique()) if not df.empty else ASPECT_LIST,
        default=None,
        placeholder="Tous les aspects",
    )

    # Application des filtres
    filtered = df.copy()

    if isinstance(date_range, tuple) and len(date_range) == 2:
        start, end = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
        filtered = filtered[
            (filtered["timestamp"] >= start)
            & (filtered["timestamp"] <= end + pd.Timedelta(days=1))
        ]

    if selected_channels:
        filtered = filtered[filtered["channel"].isin(selected_channels)]

    if selected_aspects:
        filtered = filtered[filtered["aspect"].isin(selected_aspects)]

    return filtered


# ---------------------------------------------------------------------------
# Composants visuels
# ---------------------------------------------------------------------------

def _render_kpis(nss_result: dict, df: pd.DataFrame) -> None:
    """Affiche la rangée de 4 KPI cards."""
    nss = nss_result["nss_global"]
    volume = nss_result["volume_total"]
    nb_channels = df["channel"].nunique() if not df.empty else 0

    if not df.empty and df["timestamp"].notna().any():
        min_d = df["timestamp"].min().strftime("%d/%m/%y")
        max_d = df["timestamp"].max().strftime("%d/%m/%y")
        period = f"{min_d} — {max_d}"
    else:
        period = "—"

    c1, c2, c3, c4 = st.columns(4)

    with c1:
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

    with c2:
        st.metric("Volume total", f"{volume:,}".replace(",", " "))
    with c3:
        st.metric("Canaux actifs", nb_channels)
    with c4:
        st.metric("Période", period)


def _render_heatmap(df: pd.DataFrame) -> None:
    """Affiche la matrice ABSA 5 aspects x 5 sentiments."""
    st.subheader("Matrice ABSA — Aspects x Sentiments")

    if df.empty:
        st.info("Aucune donnée pour la matrice.")
        return

    # Tableau croisé aspects (lignes) x sentiments (colonnes)
    crosstab = pd.crosstab(
        df["aspect"],
        df["sentiment_label"],
    )

    # Compléter les lignes/colonnes manquantes
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
    """Bar chart horizontal: NSS par canal."""
    st.subheader("NSS par canal")

    nss_ch = nss_result["nss_by_channel"]
    if not nss_ch:
        st.info("Aucune donnée par canal.")
        return

    ch_df = pd.DataFrame(
        [{"canal": k, "nss": v} for k, v in nss_ch.items()]
    ).sort_values("nss")

    colors = [_nss_color(v) for v in ch_df["nss"]]

    fig = go.Figure(
        go.Bar(
            x=ch_df["nss"],
            y=ch_df["canal"],
            orientation="h",
            marker_color=colors,
            text=[f"{v:+.1f}" for v in ch_df["nss"]],
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


def _render_trends(nss_result: dict) -> None:
    """Line chart: évolution NSS par semaine."""
    st.subheader("Tendance NSS hebdomadaire")

    trends = nss_result["trends"]
    if trends.empty:
        st.info("Pas assez de données pour les tendances.")
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


# ---------------------------------------------------------------------------
# Page principale
# ---------------------------------------------------------------------------

def main() -> None:
    """Rendu de la page Dashboard."""
    st.title("Dashboard ABSA + NSS")

    raw = _load_data()

    if not _PARQUET_PATH.exists():
        st.info(
            "📊 **Mode démo** — Données synthétiques. "
            "Placez un fichier annoté dans `data/processed/` pour les vraies données."
        )

    filtered = _build_filters(raw)
    nss_result = calculate_nss(filtered)

    # KPIs
    _render_kpis(nss_result, filtered)

    st.divider()

    # Matrice ABSA + NSS par canal côte à côte
    col_left, col_right = st.columns([3, 2])
    with col_left:
        _render_heatmap(filtered)
    with col_right:
        _render_nss_by_channel(nss_result)

    st.divider()

    # Tendance temporelle
    _render_trends(nss_result)


main()
