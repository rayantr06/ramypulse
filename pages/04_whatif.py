"""Page de simulation What-If pour RamyPulse.

Permet de répondre à : « Si on améliore l'emballage, quel impact sur le NSS ? »
Utilise core.whatif.simulator et des visualisations Plotly.
"""
import logging
import os
import sys

import pandas as pd
import plotly.express as px
import streamlit as st

# Assurer que le répertoire racine est dans le path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.analysis.nss_calculator import calculate_nss_by_channel
from core.whatif.simulator import simulate_whatif
from pages.whatif_helpers import (
    build_comparison_chart_data,
    build_mock_df,
    delta_arrow,
    delta_color,
    nss_label,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes UI
# ---------------------------------------------------------------------------

_ASPECTS = ["goût", "emballage", "prix", "disponibilité", "fraîcheur"]

_SCENARIOS = {
    "Améliorer": {
        "key": "améliorer",
        "icon": "🟢",
        "help": "Remonte chaque classe de sentiment d'un cran (négatif → neutre, neutre → positif…).",
    },
    "Dégrader": {
        "key": "dégrader",
        "icon": "🔴",
        "help": "Descend chaque classe de sentiment d'un cran (positif → neutre, neutre → négatif…).",
    },
    "Neutraliser": {
        "key": "neutraliser",
        "icon": "⚪",
        "help": "Retire tous les avis de cet aspect du calcul du NSS.",
    },
}

_COLOR_MAP = {"Actuel": "#3498db", "Simulé": "#2ecc71"}


# ---------------------------------------------------------------------------
# Chargement des données
# ---------------------------------------------------------------------------

@st.cache_data
def _load_data() -> pd.DataFrame:
    """Charge le DataFrame ABSA depuis data/processed/ ou fallback mock.

    Returns:
        DataFrame avec les colonnes standard RamyPulse.
    """
    processed_dir = os.path.join(os.path.dirname(__file__), "..", "data", "processed")
    raw_dir = os.path.join(os.path.dirname(__file__), "..", "data", "raw")

    for directory in (processed_dir, raw_dir):
        if os.path.exists(directory):
            parquets = sorted(f for f in os.listdir(directory) if f.endswith(".parquet"))
            if parquets:
                path = os.path.join(directory, parquets[0])
                logger.info("Données chargées : %s", path)
                return pd.read_parquet(path)

    logger.warning("Aucune donnée trouvée — mode démo avec données synthétiques.")
    return build_mock_df()


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

def main() -> None:
    """Point d'entrée de la page What-If Streamlit."""
    st.set_page_config(page_title="RamyPulse — What-If", page_icon="🔮", layout="wide")
    st.title("🔮 Simulateur What-If")
    st.markdown(
        "Explorez l'impact de chaque aspect produit sur le **Net Sentiment Score**. "
        "Sélectionnez un aspect et un scénario, puis cliquez sur **Simuler**."
    )

    df = _load_data()

    # ---- Contrôles ----
    col_aspect, col_scenario = st.columns([1, 2])

    with col_aspect:
        aspect = st.selectbox(
            "Aspect produit",
            _ASPECTS,
            help="L'aspect dont on veut simuler l'impact.",
        )

    with col_scenario:
        scenario_labels = list(_SCENARIOS.keys())
        scenario_label = st.radio(
            "Scénario",
            scenario_labels,
            horizontal=True,
            help=" · ".join(
                f"{v['icon']} **{k}** — {v['help']}" for k, v in _SCENARIOS.items()
            ),
        )
    scenario_info = _SCENARIOS[scenario_label]

    st.info(f"{scenario_info['icon']} **{scenario_label}** — {scenario_info['help']}")

    # ---- Bouton Simuler ----
    if not st.button("🚀 Simuler", type="primary", use_container_width=True):
        st.caption("Choisissez un aspect et un scénario puis appuyez sur Simuler.")
        return

    # ---- Exécution ----
    with st.spinner("Simulation en cours…"):
        nss_avant_par_canal = calculate_nss_by_channel(df)
        result = simulate_whatif(aspect, scenario_info["key"], df)

    nss_actuel = result["nss_actuel"]
    nss_simule = result["nss_simule"]
    delta = result["delta"]
    color = delta_color(delta)
    arrow = delta_arrow(delta)

    # ---- 3 metric cards ----
    st.markdown("---")
    m1, m2, m3 = st.columns(3)

    with m1:
        st.metric(
            label="NSS Actuel",
            value=f"{nss_actuel:+.1f}",
            help=f"Catégorie : {nss_label(nss_actuel)}",
        )
    with m2:
        st.metric(
            label="NSS Simulé",
            value=f"{nss_simule:+.1f}",
            help=f"Catégorie : {nss_label(nss_simule)}",
        )
    with m3:
        st.metric(
            label=f"Delta {arrow}",
            value=f"{delta:+.1f}",
            delta=f"{delta:+.1f} pts",
        )

    # ---- Bar chart comparatif par canal ----
    st.markdown("### NSS par canal — Avant vs Après")
    chart_df = build_comparison_chart_data(nss_avant_par_canal, result["nss_by_channel_simulated"])

    fig = px.bar(
        chart_df,
        x="Canal",
        y="NSS",
        color="Période",
        barmode="group",
        color_discrete_map=_COLOR_MAP,
        text_auto=".1f",
    )
    fig.update_layout(
        yaxis_title="Net Sentiment Score",
        xaxis_title="",
        legend_title="",
        height=400,
        font=dict(size=14),
    )
    fig.add_hline(y=0, line_dash="dot", line_color="gray", opacity=0.5)
    st.plotly_chart(fig, use_container_width=True)

    # ---- Interprétation ----
    st.markdown("### Interprétation")
    interp = result["interpretation"]

    # Enrichir l'interprétation avec le passage de catégorie
    label_avant = nss_label(nss_actuel)
    label_apres = nss_label(nss_simule)
    complement = ""
    if label_avant != label_apres:
        complement = (
            f" Le NSS passerait de la catégorie **{label_avant}** à **{label_apres}**."
        )

    st.markdown(
        f'<div style="padding:1rem;border-left:4px solid {color};background:#f8f9fa;'
        f'border-radius:4px;font-size:1.1rem;">'
        f"{interp}{complement}</div>",
        unsafe_allow_html=True,
    )

    # ---- Détails (expander) ----
    with st.expander("📊 Détails de la simulation"):
        st.markdown(f"**Aspect ciblé :** {aspect}")
        st.markdown(f"**Scénario :** {scenario_label} ({scenario_info['key']})")
        st.markdown(f"**Commentaires affectés :** {result['affected_count']}")
        st.markdown(f"**NSS actuel :** {nss_actuel:+.1f} ({label_avant})")
        st.markdown(f"**NSS simulé :** {nss_simule:+.1f} ({label_apres})")
        st.markdown(f"**Delta :** {delta:+.1f} points")

        st.markdown("**NSS par canal (simulé) :**")
        canal_df = pd.DataFrame(
            [
                {"Canal": k, "NSS simulé": f"{v:+.1f}"}
                for k, v in sorted(result["nss_by_channel_simulated"].items())
            ]
        )
        if not canal_df.empty:
            st.dataframe(canal_df, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
