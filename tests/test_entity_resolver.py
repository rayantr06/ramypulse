"""Tests TDD pour core/entity_resolver.py.

Couvre la résolution déterministe brand/product/product_line/sku/wilaya/competitor,
le fallback sur source_metadata, la gestion des ambiguïtés et l'enrichissement
de DataFrame.

Base SQLite :memory: — aucun fichier persistant.
"""
from __future__ import annotations

import time

import pandas as pd
import pytest

from core.business_catalog import CompetitorCatalog, ProductCatalog, WilayaCatalog
from core.database import DatabaseManager
from core.entity_resolver import EntityResolver


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def db():
    """Base SQLite en mémoire réinitialisée pour chaque test."""
    return DatabaseManager(":memory:")


@pytest.fixture
def populated_resolver(db):
    """EntityResolver avec catalogue minimal pré-rempli."""
    products = ProductCatalog(db)
    wilayas = WilayaCatalog(db)
    competitors = CompetitorCatalog(db)

    # Produits Ramy
    products.create(
        brand="Ramy",
        product_name="Jus Orange",
        product_line="Classic",
        sku="RAMY-JO-001",
        keywords_ar=["عصير برتقال"],
        keywords_arabizi=["3assir bortokal", "3sir bortokal"],
        keywords_fr=["jus orange", "jus d'orange"],
    )
    products.create(
        brand="Ramy",
        product_name="Nectar Pêche",
        product_line="Premium",
        sku="RAMY-NP-002",
        keywords_ar=["نكتار خوخ"],
        keywords_arabizi=["nectar khokh"],
        keywords_fr=["nectar pêche"],
    )
    products.create(
        brand="Ramy",
        product_name="Eau Minérale Cepure",
        product_line="Cepure",
        sku="RAMY-EM-003",
        keywords_ar=["ماء سيبور"],
        keywords_arabizi=["cepure", "ma cepure"],
        keywords_fr=["cepure", "eau cepure"],
    )
    # Produit d'une autre marque (pour test ambiguïté multi-brand)
    products.create(
        brand="Ifri",
        product_name="Eau Ifri",
        product_line="",
        sku="IFRI-EAU-001",
        keywords_arabizi=["ifri", "ma ifri"],
        keywords_fr=["eau ifri", "ifri"],
    )

    # Wilayas via seed
    wilayas.seed_from_file()

    # Concurrents
    competitors.create(
        brand_name="Hamoud Boualem",
        category="soda",
        keywords_ar=["حمود بوعلام"],
        keywords_arabizi=["hamoud", "hamoud boualem"],
        keywords_fr=["hamoud boualem"],
    )
    competitors.create(
        brand_name="Ifri",
        category="eau",
        keywords_ar=["إفري"],
        keywords_arabizi=["ifri", "ifry"],
        keywords_fr=["eau ifri"],
    )

    return EntityResolver(db)


# ---------------------------------------------------------------------------
# Résolution produit
# ---------------------------------------------------------------------------

def test_resolution_produit_par_mot_cle_francais(populated_resolver):
    """Un texte avec le nom français du produit doit résoudre brand + product."""
    result = populated_resolver.resolve_text("J'adore le jus orange de Ramy!")
    assert result["brand"] == "Ramy"
    assert result["product"] == "Jus Orange"
    assert result["sku"] == "RAMY-JO-001"


def test_resolution_produit_par_mot_cle_arabizi(populated_resolver):
    """Un texte en arabizi doit résoudre le produit correspondant."""
    result = populated_resolver.resolve_text("3assir bortokal ramy wach bghiti")
    assert result["brand"] == "Ramy"
    assert result["product"] == "Jus Orange"


def test_resolution_produit_product_line_rempli(populated_resolver):
    """product_line doit être rempli quand le produit est identifié."""
    result = populated_resolver.resolve_text("nectar pêche c'est délicieux")
    assert result["product_line"] == "Premium"
    assert result["sku"] == "RAMY-NP-002"


def test_resolution_produit_par_brand_seulement(populated_resolver):
    """Un texte mentionnant uniquement la marque doit résoudre brand sans product."""
    result = populated_resolver.resolve_text("Ramy c'est bien comme marque")
    assert result["brand"] == "Ramy"
    assert result["product"] is None


def test_priorite_produit_specifique_sur_brand(populated_resolver):
    """Un keyword produit spécifique doit primer sur un keyword de marque seul."""
    # "cepure" est un keyword produit → produit spécifique détecté
    result = populated_resolver.resolve_text("j'ai acheté cepure aujourd'hui")
    assert result["brand"] == "Ramy"
    assert result["product"] == "Eau Minérale Cepure"
    assert result["product_line"] == "Cepure"


# ---------------------------------------------------------------------------
# Résolution concurrent
# ---------------------------------------------------------------------------

def test_resolution_concurrent_par_mot_cle(populated_resolver):
    """Un texte mentionnant un concurrent doit résoudre le champ competitor."""
    result = populated_resolver.resolve_text("hamoud boualem c'est trop sucré")
    assert result["competitor"] == "Hamoud Boualem"


def test_resolution_concurrent_arabizi(populated_resolver):
    """Un texte en arabizi mentionnant un concurrent doit être résolu."""
    result = populated_resolver.resolve_text("hamoud baroud 3liha")
    assert result["competitor"] == "Hamoud Boualem"


# ---------------------------------------------------------------------------
# Résolution wilaya
# ---------------------------------------------------------------------------

def test_resolution_wilaya_par_nom_fr(populated_resolver):
    """Un texte mentionnant une wilaya par son nom français doit la résoudre."""
    result = populated_resolver.resolve_text("disponible à Béjaïa et partout")
    assert result["wilaya"] == "06"


def test_resolution_wilaya_par_variante_arabizi(populated_resolver):
    """Un texte avec une variante arabizi de wilaya doit être résolu."""
    result = populated_resolver.resolve_text("dzayer f roho wach bghit")
    assert result["wilaya"] == "16"  # Alger


def test_resolution_wilaya_oran(populated_resolver):
    """Résolution de la wilaya Oran par nom français."""
    result = populated_resolver.resolve_text("En vente à Oran ce week-end")
    assert result["wilaya"] == "31"


# ---------------------------------------------------------------------------
# Enrichissement par source_metadata
# ---------------------------------------------------------------------------

def test_enrichissement_source_metadata_brand(populated_resolver):
    """source_metadata.brand doit remplir brand quand le texte ne le contient pas."""
    result = populated_resolver.resolve_text(
        "le produit est excellent",
        source_metadata={"brand": "Ramy"},
    )
    assert result["brand"] == "Ramy"


def test_enrichissement_source_metadata_wilaya(populated_resolver):
    """source_metadata.wilaya doit remplir wilaya quand non détectée dans le texte."""
    result = populated_resolver.resolve_text(
        "j'aime bien ce goût",
        source_metadata={"wilaya": "09"},  # Blida
    )
    assert result["wilaya"] == "09"


def test_source_metadata_ne_remplace_pas_detection_texte(populated_resolver):
    """source_metadata ne doit pas écraser une détection textuelle plus précise."""
    result = populated_resolver.resolve_text(
        "jus orange c'est bon",
        source_metadata={"brand": "Inconnu"},
    )
    # Le texte contient "jus orange" → brand Ramy détecté → ne pas remplacer
    assert result["brand"] == "Ramy"
    assert result["product"] == "Jus Orange"


# ---------------------------------------------------------------------------
# Ambiguïtés
# ---------------------------------------------------------------------------

def test_ambiguite_deux_produits_differents_wilaya_none(populated_resolver):
    """Un texte ambigu (2 wilayas) doit laisser wilaya à None."""
    # "alger" et "oran" dans le même texte
    result = populated_resolver.resolve_text("disponible à alger et oran")
    # Deux wilayas détectées → ambiguïté → None
    assert result["wilaya"] is None


def test_texte_sans_match_sortie_propre(populated_resolver):
    """Un texte sans aucun mot-clé connu doit retourner tous les champs à None."""
    result = populated_resolver.resolve_text("quelque chose de totalement générique")
    assert result["brand"] is None
    assert result["product"] is None
    assert result["product_line"] is None
    assert result["sku"] is None
    assert result["wilaya"] is None
    assert result["competitor"] is None


def test_texte_vide_ne_plante_pas(populated_resolver):
    """resolve_text sur texte vide ou None ne doit pas lever d'exception."""
    result_empty = populated_resolver.resolve_text("")
    result_none = populated_resolver.resolve_text(None)
    assert result_empty["brand"] is None
    assert result_none["brand"] is None


# ---------------------------------------------------------------------------
# enrich_dataframe
# ---------------------------------------------------------------------------

def test_enrich_dataframe_ajoute_colonnes_manquantes(populated_resolver):
    """enrich_dataframe() doit ajouter les 6 colonnes métier si absentes."""
    df = pd.DataFrame({"text": ["jus orange c'est bon", "rien de spécial"]})
    enriched = populated_resolver.enrich_dataframe(df)
    for col in ["brand", "product", "product_line", "sku", "wilaya", "competitor"]:
        assert col in enriched.columns, f"Colonne manquante : {col}"


def test_enrich_dataframe_preserve_colonnes_existantes(populated_resolver):
    """enrich_dataframe() ne doit pas écraser les colonnes existantes non nulles."""
    df = pd.DataFrame({
        "text": ["jus orange c'est bon"],
        "sentiment_label": ["positif"],
        "brand": ["BrandDéjàLà"],
    })
    enriched = populated_resolver.enrich_dataframe(df)
    assert enriched["sentiment_label"].iloc[0] == "positif"
    # brand existant non nul → préservé
    assert enriched["brand"].iloc[0] == "BrandDéjàLà"


def test_enrich_dataframe_ne_modifie_pas_original(populated_resolver):
    """enrich_dataframe() ne doit pas modifier le DataFrame original."""
    df = pd.DataFrame({"text": ["hamoud boualem test"]})
    original_cols = set(df.columns)
    _ = populated_resolver.enrich_dataframe(df)
    assert set(df.columns) == original_cols


def test_enrich_dataframe_resout_correctement(populated_resolver):
    """enrich_dataframe() doit résoudre les entités de chaque ligne."""
    df = pd.DataFrame({
        "text": [
            "nectar pêche c'est bien",
            "hamoud baroud hh",
            "rien de spécial",
        ]
    })
    enriched = populated_resolver.enrich_dataframe(df)
    assert enriched["product"].iloc[0] == "Nectar Pêche"
    assert enriched["competitor"].iloc[1] == "Hamoud Boualem"
    assert enriched["brand"].iloc[2] is None


# ---------------------------------------------------------------------------
# Performance
# ---------------------------------------------------------------------------

def test_performance_batch_synthetique(populated_resolver):
    """enrich_dataframe() sur 500 lignes doit terminer en < 5 secondes."""
    texts = [
        "jus orange ramy c'est bon",
        "3assir bortokal wach bghiti",
        "hamoud boualem trop sucré",
        "disponible à Béjaïa",
        "texte générique sans entité",
    ] * 100  # 500 lignes

    df = pd.DataFrame({"text": texts})
    start = time.perf_counter()
    enriched = populated_resolver.enrich_dataframe(df)
    elapsed = time.perf_counter() - start

    assert len(enriched) == 500
    assert elapsed < 5.0, f"Trop lent : {elapsed:.2f}s pour 500 lignes"
