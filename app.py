"""Point d'entrée Streamlit pour RamyPulse.

Lance avec: streamlit run app.py
"""

import streamlit as st

st.set_page_config(
    page_title="RamyPulse",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Sidebar — navigation et branding
# ---------------------------------------------------------------------------

st.sidebar.title("RamyPulse")
st.sidebar.caption("Analyse de sentiment ABSA — Dialecte algérien")
st.sidebar.divider()

# ---------------------------------------------------------------------------
# Page d'accueil (si aucune page sélectionnée)
# ---------------------------------------------------------------------------

st.title("RamyPulse")
st.markdown(
    "Bienvenue sur **RamyPulse**, le tableau de bord d'analyse de sentiment "
    "multi-canal pour la marque Ramy."
)
st.markdown("Utilisez la barre latérale pour naviguer entre les pages.")

col1, col2 = st.columns(2)
with col1:
    st.info("**Dashboard** — KPIs, matrice ABSA, tendances")
with col2:
    st.info("**Explorateur** — Recherche et filtres avancés")
