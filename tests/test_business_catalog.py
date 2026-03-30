"""Tests TDD pour core/business_catalog.py.

Couvre le CRUD des 3 entités métier (ProductCatalog, WilayaCatalog,
CompetitorCatalog), la recherche multi-script et le chargement du seed wilayas.
Base SQLite :memory: — aucun fichier persistant créé.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.business_catalog import CompetitorCatalog, ProductCatalog, WilayaCatalog
from core.database import DatabaseManager


@pytest.fixture
def db():
    """Base SQLite en mémoire réinitialisée pour chaque test."""
    return DatabaseManager(":memory:")


@pytest.fixture
def products(db):
    """Catalogue produits branché sur la base en mémoire."""
    return ProductCatalog(db)


@pytest.fixture
def wilayas(db):
    """Catalogue wilayas branché sur la base en mémoire."""
    return WilayaCatalog(db)


@pytest.fixture
def competitors(db):
    """Catalogue concurrents branché sur la base en mémoire."""
    return CompetitorCatalog(db)


def test_product_create_retourne_id(products):
    """create() doit retourner un identifiant textuel non vide."""
    pid = products.create(brand="Ramy", product_name="Jus orange")
    assert isinstance(pid, str)
    assert pid.startswith("prod-")


def test_product_get_retourne_enregistrement(products):
    """get() doit retourner le produit créé avec toutes ses clés."""
    pid = products.create(
        brand="Ramy",
        product_name="Nectar pêche",
        sku="RAMY-NPC-001",
        category="nectar",
        keywords_ar=["نكتار"],
        keywords_arabizi=["nectar"],
        keywords_fr=["nectar pêche"],
    )
    product = products.get(pid)
    assert product is not None
    assert product["brand"] == "Ramy"
    assert product["product_name"] == "Nectar pêche"
    assert product["sku"] == "RAMY-NPC-001"
    assert "نكتار" in product["keywords_ar"]
    assert "nectar" in product["keywords_arabizi"]


def test_product_get_inexistant_retourne_none(products):
    """get() doit retourner None pour un ID qui n'existe pas."""
    assert products.get("prod-inexistant") is None


def test_product_list_retourne_tous(products):
    """list() sans filtre doit retourner tous les produits créés."""
    products.create(brand="Ramy", product_name="Jus raisin")
    products.create(brand="Ramy", product_name="Eau Cepure")
    assert len(products.list()) == 2


def test_product_list_filtre_par_categorie(products):
    """list(category=...) doit ne retourner que les produits de cette catégorie."""
    products.create(brand="Ramy", product_name="Jus orange", category="jus")
    products.create(brand="Ramy", product_name="Nectar pêche", category="nectar")
    jus = products.list(category="jus")
    assert len(jus) == 1
    assert jus[0]["product_name"] == "Jus orange"


def test_product_list_filtre_par_is_active(products):
    """list(is_active=False) doit ne retourner que les produits inactifs."""
    products.create(brand="Ramy", product_name="Ancien produit", is_active=False)
    products.create(brand="Ramy", product_name="Produit actif", is_active=True)
    inactifs = products.list(is_active=False)
    assert len(inactifs) == 1
    assert inactifs[0]["product_name"] == "Ancien produit"


def test_product_update_modifie_champ(products):
    """update() doit modifier le champ demandé et retourner True."""
    pid = products.create(brand="Ramy", product_name="Jus citron")
    result = products.update(pid, product_name="Jus citron premium")
    assert result is True
    assert products.get(pid)["product_name"] == "Jus citron premium"


def test_product_update_inexistant_retourne_false(products):
    """update() sur un ID inexistant doit retourner False."""
    assert products.update("prod-inexistant", product_name="Fantôme") is False


def test_product_delete_supprime(products):
    """delete() doit supprimer le produit et retourner True."""
    pid = products.create(brand="Ramy", product_name="À supprimer")
    assert products.delete(pid) is True
    assert products.get(pid) is None


def test_product_delete_inexistant_retourne_false(products):
    """delete() sur un ID inexistant doit retourner False."""
    assert products.delete("prod-inexistant") is False


def test_product_search_by_keyword_arabizi(products):
    """search_by_keyword() doit trouver un produit par son mot-clé arabizi."""
    products.create(
        brand="Ramy",
        product_name="Jus raisin",
        keywords_arabizi=["3assir raisin", "3sir"],
    )
    results = products.search_by_keyword("3assir")
    assert len(results) == 1
    assert results[0]["product_name"] == "Jus raisin"


def test_product_search_by_keyword_arabe(products):
    """search_by_keyword() doit trouver un produit par son mot-clé en arabe."""
    products.create(
        brand="Ramy",
        product_name="Jus pomme",
        keywords_ar=["عصير تفاح"],
    )
    results = products.search_by_keyword("تفاح")
    assert len(results) == 1


def test_product_search_by_keyword_nom_produit(products):
    """search_by_keyword() doit trouver via le nom du produit."""
    products.create(brand="Ramy", product_name="Limonade")
    assert len(products.search_by_keyword("limonade")) == 1
    assert len(products.search_by_keyword("inexistant_xyz")) == 0


def test_wilaya_seed_charge_58_wilayas(wilayas):
    """seed_from_file() doit insérer 58 wilayas depuis le fichier JSON de seed."""
    inserted = wilayas.seed_from_file()
    assert inserted == 58
    assert len(wilayas.list()) == 58


def test_wilaya_seed_idempotent(wilayas):
    """seed_from_file() appelé deux fois ne doit pas dupliquer les wilayas."""
    wilayas.seed_from_file()
    second_insert = wilayas.seed_from_file()
    assert second_insert == 0
    assert len(wilayas.list()) == 58


def test_wilaya_get_par_code(wilayas):
    """get('06') doit retourner Béjaïa avec ses variantes arabizi."""
    wilayas.seed_from_file()
    bejaia = wilayas.get("06")
    assert bejaia is not None
    assert bejaia["wilaya_name_fr"] == "Béjaïa"
    assert "bejaia" in bejaia["keywords_arabizi"]


def test_wilaya_list_filtre_region_est(wilayas):
    """list(region='Est') doit retourner uniquement les wilayas de l'Est."""
    wilayas.seed_from_file()
    est = wilayas.list(region="Est")
    assert len(est) > 0
    assert all(w["region"] == "Est" for w in est)


def test_wilaya_create_update_delete(wilayas):
    """CRUD complet sur une wilaya créée manuellement."""
    wilayas.create("99", "Test Wilaya", "تست", ["test", "twilaya"], "Centre")
    wilaya = wilayas.get("99")
    assert wilaya["wilaya_name_fr"] == "Test Wilaya"

    updated = wilayas.update("99", wilaya_name_fr="Test Wilaya Modifiée")
    assert updated is True
    assert wilayas.get("99")["wilaya_name_fr"] == "Test Wilaya Modifiée"

    deleted = wilayas.delete("99")
    assert deleted is True
    assert wilayas.get("99") is None


def test_wilaya_search_arabizi(wilayas):
    """search_by_keyword('dzayer') doit trouver Alger via ses variantes arabizi."""
    wilayas.seed_from_file()
    results = wilayas.search_by_keyword("dzayer")
    assert len(results) >= 1
    assert any(w["wilaya_name_fr"] == "Alger" for w in results)


def test_wilaya_search_nom_fr(wilayas):
    """search_by_keyword('oran') doit trouver Oran via son nom français."""
    wilayas.seed_from_file()
    results = wilayas.search_by_keyword("oran")
    assert any(w["wilaya_name_fr"] == "Oran" for w in results)


def test_competitor_create_retourne_id(competitors):
    """create() doit retourner un identifiant textuel non vide."""
    cid = competitors.create(brand_name="Ifri")
    assert isinstance(cid, str)
    assert cid.startswith("comp-")


def test_competitor_get_retourne_enregistrement(competitors):
    """get() doit retourner le concurrent avec ses mots-clés multi-scripts."""
    cid = competitors.create(
        brand_name="Hamoud Boualem",
        category="soda",
        keywords_ar=["حمود بوعلام"],
        keywords_arabizi=["hamoud", "hamoud boualem"],
        keywords_fr=["hamoud boualem"],
    )
    competitor = competitors.get(cid)
    assert competitor is not None
    assert competitor["brand_name"] == "Hamoud Boualem"
    assert "حمود بوعلام" in competitor["keywords_ar"]
    assert "hamoud" in competitor["keywords_arabizi"]


def test_competitor_list_filtre_categorie(competitors):
    """list(category='eau') ne retourne que les concurrents eau."""
    competitors.create(brand_name="Ifri", category="eau")
    competitors.create(brand_name="Hamoud", category="soda")
    eau = competitors.list(category="eau")
    assert len(eau) == 1
    assert eau[0]["brand_name"] == "Ifri"


def test_competitor_list_filtre_is_active(competitors):
    """list(is_active=False) doit ne retourner que les concurrents inactifs."""
    competitors.create(brand_name="Ancien", is_active=False)
    competitors.create(brand_name="Actif", is_active=True)
    inactifs = competitors.list(is_active=False)
    assert len(inactifs) == 1
    assert inactifs[0]["brand_name"] == "Ancien"


def test_competitor_update_modifie_champ(competitors):
    """update() doit modifier le champ demandé et retourner True."""
    cid = competitors.create(brand_name="Ifri")
    result = competitors.update(cid, brand_name="Ifri Premium")
    assert result is True
    assert competitors.get(cid)["brand_name"] == "Ifri Premium"


def test_competitor_update_inexistant_retourne_false(competitors):
    """update() sur un ID inexistant doit retourner False."""
    assert competitors.update("comp-inexistant", brand_name="Fantôme") is False


def test_competitor_delete_supprime(competitors):
    """delete() doit supprimer le concurrent et retourner True."""
    cid = competitors.create(brand_name="À supprimer")
    assert competitors.delete(cid) is True
    assert competitors.get(cid) is None


def test_competitor_delete_inexistant_retourne_false(competitors):
    """delete() sur un ID inexistant doit retourner False."""
    assert competitors.delete("comp-inexistant") is False


def test_competitor_search_by_keyword_arabizi(competitors):
    """search_by_keyword() doit trouver un concurrent par mot-clé arabizi."""
    competitors.create(
        brand_name="Hamoud Boualem",
        keywords_arabizi=["hamoud", "hamoud boualem"],
    )
    results = competitors.search_by_keyword("hamoud")
    assert len(results) == 1
    assert results[0]["brand_name"] == "Hamoud Boualem"


def test_competitor_search_by_keyword_arabe(competitors):
    """search_by_keyword() doit trouver un concurrent par mot-clé arabe."""
    competitors.create(
        brand_name="Ifri",
        keywords_ar=["إفري"],
    )
    results = competitors.search_by_keyword("إفري")
    assert len(results) == 1


def test_competitor_search_nom_marque(competitors):
    """search_by_keyword() doit trouver via brand_name."""
    competitors.create(brand_name="Rouiba")
    assert len(competitors.search_by_keyword("rouiba")) == 1
    assert len(competitors.search_by_keyword("inexistant_xyz")) == 0
