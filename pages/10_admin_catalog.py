"""Page Streamlit d'administration du catalogue metier."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.business_catalog import CompetitorCatalog, ProductCatalog, WilayaCatalog
from core.database import DatabaseManager
from ui_helpers.phase1_admin_helpers import (
    build_catalog_frame,
    compute_catalog_metrics,
    parse_keywords,
)


@st.cache_resource
def _get_catalogs() -> tuple[ProductCatalog, WilayaCatalog, CompetitorCatalog]:
    """Initialise la base SQLite et les trois catalogues metier."""
    database = DatabaseManager()
    database.create_tables()
    return (
        ProductCatalog(database),
        WilayaCatalog(database),
        CompetitorCatalog(database),
    )


def _render_product_tab(products: ProductCatalog) -> None:
    """Affiche la vue produits."""
    all_products = products.list()
    brand_filter = st.selectbox(
        "Filtre marque",
        options=["all"] + sorted({row["brand"] for row in all_products if row.get("brand")}),
        key="product_brand_filter",
    )
    state_filter = st.selectbox(
        "Etat",
        options=["all", "active", "inactive"],
        key="product_state_filter",
    )

    filtered = all_products
    if brand_filter != "all":
        filtered = [row for row in filtered if row.get("brand") == brand_filter]
    if state_filter == "active":
        filtered = [row for row in filtered if bool(row.get("is_active"))]
    elif state_filter == "inactive":
        filtered = [row for row in filtered if not bool(row.get("is_active"))]

    frame = build_catalog_frame(
        filtered,
        ["product_id", "brand", "product_line", "product_name", "sku", "category", "is_active"],
    )
    if frame.empty:
        st.info("Aucun produit catalogue pour le moment.")
    else:
        st.dataframe(frame, use_container_width=True, hide_index=True)

    with st.form("create_product"):
        st.markdown("**Ajouter un produit**")
        col1, col2 = st.columns(2)
        with col1:
            brand = st.text_input("Brand", key="product_brand")
            product_line = st.text_input("Product line", key="product_line")
            product_name = st.text_input("Product name", key="product_name")
            sku = st.text_input("SKU", key="product_sku")
        with col2:
            category = st.text_input("Category", key="product_category")
            keywords_fr = st.text_input("Keywords FR", key="product_keywords_fr")
            keywords_ar = st.text_input("Keywords AR", key="product_keywords_ar")
            keywords_arabizi = st.text_input("Keywords Arabizi", key="product_keywords_arabizi")
        if st.form_submit_button("Creer le produit"):
            try:
                products.create(
                    brand=brand,
                    product_line=product_line,
                    product_name=product_name,
                    sku=sku or None,
                    category=category,
                    keywords_fr=parse_keywords(keywords_fr),
                    keywords_ar=parse_keywords(keywords_ar),
                    keywords_arabizi=parse_keywords(keywords_arabizi),
                )
                st.success("Produit cree.")
                st.rerun()
            except Exception as exc:  # pragma: no cover - garde-fou UI
                st.error(f"Echec creation produit: {exc}")


def _render_wilaya_tab(wilayas: WilayaCatalog) -> None:
    """Affiche la vue wilayas."""
    all_wilayas = wilayas.list()
    region_filter = st.selectbox(
        "Filtre region",
        options=["all"] + sorted({row["region"] for row in all_wilayas if row.get("region")}),
        key="wilaya_region_filter",
    )
    filtered = all_wilayas if region_filter == "all" else [row for row in all_wilayas if row.get("region") == region_filter]

    frame = build_catalog_frame(
        filtered,
        ["wilaya_code", "wilaya_name_fr", "wilaya_name_ar", "region"],
    )
    if frame.empty:
        st.info("Aucune wilaya chargee pour le moment.")
    else:
        st.dataframe(frame, use_container_width=True, hide_index=True)

    action_col, _ = st.columns([1, 3])
    with action_col:
        if st.button("Charger les 58 wilayas"):
            inserted = wilayas.seed_from_file()
            st.success(f"Seed termine: {inserted} wilayas inserees.")
            st.rerun()

    with st.form("create_wilaya"):
        st.markdown("**Ajouter une wilaya**")
        col1, col2 = st.columns(2)
        with col1:
            wilaya_code = st.text_input("Code", key="wilaya_code")
            wilaya_name_fr = st.text_input("Nom FR", key="wilaya_name_fr")
            wilaya_name_ar = st.text_input("Nom AR", key="wilaya_name_ar")
        with col2:
            keywords_arabizi = st.text_input("Keywords Arabizi", key="wilaya_keywords_arabizi")
            region = st.text_input("Region", key="wilaya_region")
        if st.form_submit_button("Creer la wilaya"):
            try:
                wilayas.create(
                    wilaya_code=wilaya_code,
                    wilaya_name_fr=wilaya_name_fr,
                    wilaya_name_ar=wilaya_name_ar,
                    keywords_arabizi=parse_keywords(keywords_arabizi),
                    region=region,
                )
                st.success("Wilaya creee.")
                st.rerun()
            except Exception as exc:  # pragma: no cover - garde-fou UI
                st.error(f"Echec creation wilaya: {exc}")


def _render_competitor_tab(competitors: CompetitorCatalog) -> None:
    """Affiche la vue concurrents."""
    all_competitors = competitors.list()
    category_filter = st.selectbox(
        "Filtre categorie",
        options=["all"] + sorted({row["category"] for row in all_competitors if row.get("category")}),
        key="competitor_category_filter",
    )
    filtered = all_competitors if category_filter == "all" else [row for row in all_competitors if row.get("category") == category_filter]

    frame = build_catalog_frame(
        filtered,
        ["competitor_id", "brand_name", "category", "is_active"],
    )
    if frame.empty:
        st.info("Aucun concurrent catalogue pour le moment.")
    else:
        st.dataframe(frame, use_container_width=True, hide_index=True)

    with st.form("create_competitor"):
        st.markdown("**Ajouter un concurrent**")
        col1, col2 = st.columns(2)
        with col1:
            brand_name = st.text_input("Brand name", key="competitor_brand_name")
            category = st.text_input("Category", key="competitor_category")
        with col2:
            keywords_fr = st.text_input("Keywords FR", key="competitor_keywords_fr")
            keywords_ar = st.text_input("Keywords AR", key="competitor_keywords_ar")
            keywords_arabizi = st.text_input("Keywords Arabizi", key="competitor_keywords_arabizi")
        if st.form_submit_button("Creer le concurrent"):
            try:
                competitors.create(
                    brand_name=brand_name,
                    category=category,
                    keywords_fr=parse_keywords(keywords_fr),
                    keywords_ar=parse_keywords(keywords_ar),
                    keywords_arabizi=parse_keywords(keywords_arabizi),
                )
                st.success("Concurrent cree.")
                st.rerun()
            except Exception as exc:  # pragma: no cover - garde-fou UI
                st.error(f"Echec creation concurrent: {exc}")


def main() -> None:
    """Rendu de la page Admin Catalog."""
    st.title("Admin Catalog")

    products, wilayas, competitors = _get_catalogs()
    product_rows = products.list()
    wilaya_rows = wilayas.list()
    competitor_rows = competitors.list()
    metrics = compute_catalog_metrics(product_rows, wilaya_rows, competitor_rows)

    col1, col2, col3 = st.columns(3)
    col1.metric("Produits", metrics["products"])
    col2.metric("Wilayas", metrics["wilayas"])
    col3.metric("Concurrents", metrics["competitors"])

    st.divider()
    tab_products, tab_wilayas, tab_competitors = st.tabs(
        ["Produits", "Wilayas", "Concurrents"]
    )
    with tab_products:
        _render_product_tab(products)
    with tab_wilayas:
        _render_wilaya_tab(wilayas)
    with tab_competitors:
        _render_competitor_tab(competitors)


main()
