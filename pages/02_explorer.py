"""Explorateur de donnees avec filtres avances pour RamyPulse."""

import logging
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import ASPECT_LIST, CHANNELS, DATA_DIR, SENTIMENT_LABELS
from pages.phase1_dashboard_helpers import (
    apply_dataframe_filters,
    build_available_filters,
    build_explorer_display_columns,
    default_date_range,
    format_missing_dimensions,
    missing_filter_columns,
)
from pages.whatif_helpers import build_mock_df

logger = logging.getLogger(__name__)

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

_COLUMN_LABELS = {
    "text": "Texte",
    "sentiment_label": "Sentiment",
    "aspect": "Aspect",
    "channel": "Canal",
    "product": "Produit",
    "wilaya": "Wilaya",
    "timestamp": "Date",
}

_COLUMN_WIDTHS = {
    "text": 4,
    "sentiment_label": 1,
    "aspect": 1,
    "channel": 1,
    "product": 1,
    "wilaya": 1,
    "timestamp": 1,
}


@st.cache_data(ttl=300)
def _load_data() -> pd.DataFrame:
    """Charge le dataset annote depuis le Parquet ou fallback demo."""
    if _PARQUET_PATH.exists():
        df = pd.read_parquet(_PARQUET_PATH)
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        return df
    logger.warning("Aucune donnee trouvee - mode demo avec donnees synthetiques.")
    df = build_mock_df(n=500)
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    return df


def _build_filters(df: pd.DataFrame) -> pd.DataFrame:
    """Construit les filtres sidebar et retourne le DataFrame filtre."""
    st.sidebar.header("Filtres explorateur")

    available_filters = build_available_filters(
        df,
        ["channel", "aspect", "sentiment_label", "product", "wilaya"],
    )
    missing_dimensions = missing_filter_columns(df, ["product", "wilaya"])
    if missing_dimensions:
        st.sidebar.caption(format_missing_dimensions(missing_dimensions))

    selected_channels = st.sidebar.multiselect(
        "Canaux",
        options=available_filters["channel"] if not df.empty else CHANNELS,
        default=None,
        placeholder="Tous les canaux",
        key="explorer_channels",
    )
    selected_aspects = st.sidebar.multiselect(
        "Aspects",
        options=available_filters["aspect"] if not df.empty else ASPECT_LIST,
        default=None,
        placeholder="Tous les aspects",
        key="explorer_aspects",
    )
    selected_sentiments = st.sidebar.multiselect(
        "Sentiments",
        options=available_filters["sentiment_label"] if not df.empty else SENTIMENT_LABELS,
        default=None,
        placeholder="Tous les sentiments",
        key="explorer_sentiments",
    )

    selected_products: list[str] = []
    if "product" in df.columns:
        selected_products = st.sidebar.multiselect(
            "Produits",
            options=available_filters["product"],
            default=None,
            placeholder="Tous les produits",
            key="explorer_products",
        )

    selected_wilayas: list[str] = []
    if "wilaya" in df.columns:
        selected_wilayas = st.sidebar.multiselect(
            "Wilayas",
            options=available_filters["wilaya"],
            default=None,
            placeholder="Toutes les wilayas",
            key="explorer_wilayas",
        )

    min_date, max_date = default_date_range(df)
    date_range = st.sidebar.date_input(
        "Periode",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        key="explorer_dates",
    )

    return apply_dataframe_filters(
        df,
        {
            "channel": selected_channels,
            "aspect": selected_aspects,
            "sentiment_label": selected_sentiments,
            "product": selected_products,
            "wilaya": selected_wilayas,
            "date_range": date_range,
        },
    )


def _render_counter(filtered: pd.DataFrame, total: int) -> None:
    """Affiche le compteur de resultats."""
    st.markdown(f"**{len(filtered)} resultats** sur {total} total")


def _render_donut(filtered: pd.DataFrame) -> None:
    """Affiche la repartition des sentiments."""
    if filtered.empty:
        st.info("Aucune donnee pour le graphique.")
        return

    counts = filtered["sentiment_label"].value_counts().reindex(SENTIMENT_LABELS, fill_value=0)
    colors = [_SENTIMENT_COLORS.get(label, "#999999") for label in counts.index]

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
    fig.update_layout(height=350, margin=dict(l=10, r=10, t=10, b=10), showlegend=False)
    st.plotly_chart(fig, use_container_width=True)


def _format_cell_value(row: pd.Series, column: str) -> str:
    """Formate une valeur de cellule pour l'affichage compact."""
    value = row.get(column, "")
    if column == "text":
        text = str(value)
        return text[:_TEXT_TRUNCATE] + "..." if len(text) > _TEXT_TRUNCATE else text
    if column == "timestamp":
        if pd.isna(value):
            return "-"
        return pd.to_datetime(value).strftime("%d/%m/%Y %H:%M")
    if pd.isna(value):
        return "-"
    return str(value)


def _render_table(filtered: pd.DataFrame) -> None:
    """Affiche un tableau pagine avec colonnes metier si disponibles."""
    if filtered.empty:
        st.info("Aucun resultat avec les filtres actuels.")
        return

    display = filtered.sort_values("timestamp", ascending=False).reset_index(drop=True)
    total_pages = max(1, -(-len(display) // _PAGE_SIZE))
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
    display_columns = build_explorer_display_columns(page_df)
    widths = [_COLUMN_WIDTHS[column] for column in display_columns]

    st.caption(f"Page {page}/{total_pages} - lignes {start + 1} a {end}")

    header = st.columns(widths)
    for widget, column in zip(header, display_columns):
        widget.markdown(f"**{_COLUMN_LABELS[column]}**")
    st.divider()

    for _, row in page_df.iterrows():
        widgets = st.columns(widths)
        for widget, column in zip(widgets, display_columns):
            value = _format_cell_value(row, column)
            if column == "sentiment_label":
                color = _SENTIMENT_COLORS.get(str(row.get("sentiment_label", "")), "#999999")
                widget.markdown(
                    f'<span style="color:{color};font-weight:bold;">{value}</span>',
                    unsafe_allow_html=True,
                )
            elif column == "text":
                widget.markdown(value)
            else:
                widget.caption(value)

        with st.expander("Voir le detail"):
            st.markdown(f"**Texte complet:** {row.get('text', '')}")
            st.markdown(f"**Confiance:** {float(row.get('confidence', 0.0)):.1%}")
            if "product" in row.index:
                st.markdown(f"**Produit:** {row.get('product') or '-'}")
            if "wilaya" in row.index:
                st.markdown(f"**Wilaya:** {row.get('wilaya') or '-'}")
            source = row.get("source_url", "")
            if source:
                if str(source).startswith("http"):
                    st.markdown(f"**Source:** [{source}]({source})")
                else:
                    st.markdown(f"**Source:** `{source}`")
            else:
                st.markdown("**Source:** non disponible")


def main() -> None:
    """Rendu de la page Explorateur."""
    st.title("Explorateur de donnees")

    raw = _load_data()
    if not _PARQUET_PATH.exists():
        st.info(
            "Mode demo - donnees synthetiques. "
            "Placez un fichier annote dans `data/processed/` pour les vraies donnees."
        )

    filtered = _build_filters(raw)
    _render_counter(filtered, len(raw))

    st.divider()
    col_chart, col_table = st.columns([1, 3])
    with col_chart:
        st.subheader("Repartition")
        _render_donut(filtered)
    with col_table:
        st.subheader("Donnees")
        _render_table(filtered)


main()
