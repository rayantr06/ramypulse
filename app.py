"""Point d'entree Streamlit pour RamyPulse.

Lance avec: streamlit run app.py
"""

import streamlit as st

st.set_page_config(
    page_title="RamyPulse",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.sidebar.title("RamyPulse")
st.sidebar.caption("Analyse de sentiment ABSA - Dialecte algerien")
st.sidebar.divider()

st.title("RamyPulse")
st.markdown(
    "Bienvenue sur **RamyPulse**, la couche d'analyse et de pilotage "
    "multi-canal pour la marque Ramy."
)
st.markdown("Utilisez la barre laterale pour naviguer entre les pages.")

row1 = st.columns(3)
row2 = st.columns(3)

with row1[0]:
    st.info("📊 **Dashboard** - KPIs, matrice ABSA, tendances et filtres metier")
with row1[1]:
    st.info("🔍 **Explorateur** - Recherche detaillee, filtres avances, colonnes metier")
with row1[2]:
    st.info("💬 **Chat Q&A** - Questions en langage naturel + sources")

with row2[0]:
    st.info("🔮 **What-If** - Simulation d'impact par aspect")
with row2[1]:
    st.info("🗂️ **Admin Sources** - Registre SQLite des sources surveillees")
with row2[2]:
    st.info("📚 **Admin Catalog** - Produits, wilayas et concurrents")
