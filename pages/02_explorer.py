"""Explorateur de données avec filtres avancés pour RamyPulse."""

import logging
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import ASPECT_LIST, CHANNELS, DATA_DIR, SENTIMENT_LABELS
from pages.whatif_helpers import build_mock_df

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

_PARQUET_PATH = DATA_DIR / "processed" / "annotated.parquet"
_PAGE_SIZE = 50
_TEXT_TRUNCATE = 100

_SENTIMENT_COLORS = {
    "très_positif": "#2E7D32",
    "positif": "#66BB6A",
    "neutre": "#BDBDBD",
    "négatif": "#FF7043",
    "très_négatif": "#E53935",
}


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
# Filtres
# ---------------------------------------------------------------------------

def _build_filters(df: pd.DataFrame) -> pd.DataFrame:
    """Construit les filtres dans la sidebar et retourne le DataFrame filtré."""
    st.sidebar.header("Filtres explorateur")

    # Canaux
    selected_channels = st.sidebar.multiselect(
        "Canaux",
        options=sorted(df["channel"].dropna().unique()) if not df.empty else CHANNELS,
        default=None,
        placeholder="Tous les canaux",
        key="explorer_channels",
    )

    # Aspects
    selected_aspects = st.sidebar.multiselect(
        "Aspects",
        options=sorted(df["aspect"].dropna().unique()) if not df.empty else ASPECT_LIST,
        default=None,
        placeholder="Tous les aspects",
        key="explorer_aspects",
    )

    # Sentiments
    selected_sentiments = st.sidebar.multiselect(
        "Sentiments",
        options=SENTIMENT_LABELS,
        default=None,
        placeholder="Tous les sentiments",
        key="explorer_sentiments",
    )

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
        key="explorer_dates",
    )

    # Application des filtres
    filtered = df.copy()

    if selected_channels:
        filtered = filtered[filtered["channel"].isin(selected_channels)]

    if selected_aspects:
        filtered = filtered[filtered["aspect"].isin(selected_aspects)]

    if selected_sentiments:
        filtered = filtered[filtered["sentiment_label"].isin(selected_sentiments)]

    if isinstance(date_range, tuple) and len(date_range) == 2:
        start = pd.Timestamp(date_range[0])
        end = pd.Timestamp(date_range[1])
        filtered = filtered[
            (filtered["timestamp"] >= start)
            & (filtered["timestamp"] <= end + pd.Timedelta(days=1))
        ]

    return filtered


# ---------------------------------------------------------------------------
# Composants visuels
# ---------------------------------------------------------------------------

def _render_counter(filtered: pd.DataFrame, total: int) -> None:
    """Affiche le compteur de résultats."""
    n = len(filtered)
    st.markdown(f"**{n} résultats** sur {total} total")


def _render_donut(filtered: pd.DataFrame) -> None:
    """Donut chart: répartition des sentiments."""
    if filtered.empty:
        st.info("Aucune donnée pour le graphique.")
        return

    counts = (
        filtered["sentiment_label"]
        .value_counts()
        .reindex(SENTIMENT_LABELS, fill_value=0)
    )
    colors = [_SENTIMENT_COLORS.get(s, "#999") for s in counts.index]

    fig = px.pie(
        names=counts.index,
        values=counts.values,
        hole=0.45,
        color_discrete_sequence=colors,
    )
    fig.update_traces(
        textinfo="label+percent",
        hovertemplate="%{label}: %{value} (%{percent})<extra></extra>",
    )
    fig.update_layout(
        height=350,
        margin=dict(l=10, r=10, t=10, b=10),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_table(filtered: pd.DataFrame) -> None:
    """Tableau paginé avec expander par ligne."""
    if filtered.empty:
        st.info("Aucun résultat avec les filtres actuels.")
        return

    # Tri par date décroissante
    display = filtered.sort_values("timestamp", ascending=False).reset_index(drop=True)

    # Pagination
    total_pages = max(1, -(-len(display) // _PAGE_SIZE))  # ceil division
    page = st.number_input(
        "Page",
        min_value=1,
        max_value=total_pages,
        value=1,
        step=1,
        key="explorer_page",
    )
    start = (page - 1) * _PAGE_SIZE
    end = min(start + _PAGE_SIZE, len(display))
    page_df = display.iloc[start:end]

    st.caption(f"Page {page}/{total_pages} — lignes {start + 1} à {end}")

    # Affichage des lignes
    for _, row in page_df.iterrows():
        text = str(row.get("text", ""))
        truncated = text[:_TEXT_TRUNCATE] + "..." if len(text) > _TEXT_TRUNCATE else text
        sentiment = row.get("sentiment_label", "")
        aspect = row.get("aspect", "")
        channel = row.get("channel", "")
        ts = row.get("timestamp", None)
        source = row.get("source_url", "")
        confidence = row.get("confidence", 0.0)

        date_str = ts.strftime("%d/%m/%Y %H:%M") if pd.notna(ts) else "—"
        color = _SENTIMENT_COLORS.get(sentiment, "#999")

        # Ligne compacte
        cols = st.columns([4, 1, 1, 1, 1])
        with cols[0]:
            st.markdown(truncated)
        with cols[1]:
            st.markdown(
                f'<span style="color:{color};font-weight:bold;">{sentiment}</span>',
                unsafe_allow_html=True,
            )
        with cols[2]:
            st.caption(aspect)
        with cols[3]:
            st.caption(channel)
        with cols[4]:
            st.caption(date_str)

        # Expander: texte complet + source cliquable
        with st.expander("Voir le détail"):
            st.markdown(f"**Texte complet:** {text}")
            st.markdown(f"**Confiance:** {confidence:.1%}")
            if source:
                if source.startswith("http"):
                    st.markdown(f"**Source:** [{source}]({source})")
                else:
                    st.markdown(f"**Source:** `{source}`")
            else:
                st.markdown("**Source:** non disponible")


# ---------------------------------------------------------------------------
# Page principale
# ---------------------------------------------------------------------------

def main() -> None:
    """Rendu de la page Explorateur."""
    st.title("Explorateur de données")

    raw = _load_data()

    if not _PARQUET_PATH.exists():
        st.info(
            "🔍 **Mode démo** — Données synthétiques. "
            "Placez un fichier annoté dans `data/processed/` pour les vraies données."
        )

    filtered = _build_filters(raw)

    # Counter
    _render_counter(filtered, len(raw))

    st.divider()

    # Layout: donut à gauche, tableau à droite
    col_chart, col_table = st.columns([1, 3])

    with col_chart:
        st.subheader("Répartition")
        _render_donut(filtered)

    with col_table:
        st.subheader("Données")
        # En-tête du tableau
        header = st.columns([4, 1, 1, 1, 1])
        header[0].markdown("**Texte**")
        header[1].markdown("**Sentiment**")
        header[2].markdown("**Aspect**")
        header[3].markdown("**Canal**")
        header[4].markdown("**Date**")
        st.divider()
        _render_table(filtered)


main()
