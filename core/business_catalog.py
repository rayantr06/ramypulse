"""Catalogue métier RamyPulse : Produits, Wilayas, Concurrents.

Ce module est la référence utilisée par l'Entity Resolver pour rattacher
les mentions extraites des réseaux sociaux aux entités métier connues.

Chaque catalogue expose une interface CRUD complète et une recherche
multi-script (arabe / arabizi / français) via search_by_keyword().

Dépendance : core/database.py (DatabaseManager).
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

from core.database import DatabaseManager

logger = logging.getLogger(__name__)

_SEED_WILAYAS_PATH = Path(__file__).parent.parent / "data" / "seed" / "wilayas.json"


# ---------------------------------------------------------------------------
# DDL
# ---------------------------------------------------------------------------

_DDL_PRODUCTS = """
CREATE TABLE IF NOT EXISTS products (
    product_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    brand         TEXT    NOT NULL,
    product_line  TEXT    NOT NULL DEFAULT '',
    product_name  TEXT    NOT NULL,
    sku           TEXT    UNIQUE,
    category      TEXT    NOT NULL DEFAULT '',
    keywords_ar   TEXT    NOT NULL DEFAULT '[]',
    keywords_arabizi TEXT NOT NULL DEFAULT '[]',
    keywords_fr   TEXT    NOT NULL DEFAULT '[]',
    is_active     INTEGER NOT NULL DEFAULT 1
)
"""

_DDL_WILAYAS = """
CREATE TABLE IF NOT EXISTS wilayas (
    wilaya_code      TEXT PRIMARY KEY,
    name_fr          TEXT NOT NULL,
    name_ar          TEXT NOT NULL DEFAULT '',
    keywords_arabizi TEXT NOT NULL DEFAULT '[]',
    region           TEXT NOT NULL DEFAULT ''
)
"""

_DDL_COMPETITORS = """
CREATE TABLE IF NOT EXISTS competitors (
    competitor_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    brand_name     TEXT    NOT NULL UNIQUE,
    category       TEXT    NOT NULL DEFAULT '',
    keywords_ar    TEXT    NOT NULL DEFAULT '[]',
    keywords_arabizi TEXT  NOT NULL DEFAULT '[]',
    keywords_fr    TEXT    NOT NULL DEFAULT '[]',
    is_active      INTEGER NOT NULL DEFAULT 1
)
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _json_encode(value: Any) -> str:
    """Sérialise une valeur Python en JSON compact.

    Args:
        value: Valeur à sérialiser (liste, dict, etc.).

    Returns:
        Chaîne JSON.
    """
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def _json_decode(value: str) -> Any:
    """Désérialise une chaîne JSON en valeur Python.

    Args:
        value: Chaîne JSON à parser.

    Returns:
        Valeur Python (liste, dict, etc.) ou chaîne originale si échec.
    """
    if not value:
        return []
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return value


def _row_to_dict(row) -> dict:
    """Convertit une sqlite3.Row en dictionnaire Python standard.

    Args:
        row: Ligne SQLite (sqlite3.Row ou None).

    Returns:
        Dictionnaire ou None si row est None.
    """
    if row is None:
        return None
    return dict(row)


def _decode_keywords(record: dict, fields: list[str]) -> dict:
    """Décode les champs JSON keywords d'un enregistrement.

    Args:
        record: Dictionnaire d'enregistrement.
        fields: Liste des champs à décoder (contiennent du JSON).

    Returns:
        Enregistrement avec les champs décodés.
    """
    if record is None:
        return None
    for field in fields:
        if field in record:
            record[field] = _json_decode(record[field])
    return record


# ---------------------------------------------------------------------------
# ProductCatalog
# ---------------------------------------------------------------------------

class ProductCatalog:
    """Catalogue des produits Ramy avec CRUD et recherche multi-script.

    Gère les produits (marque, gamme, SKU) avec leurs variantes de mots-clés
    en arabe, arabizi et français pour la détection dans les mentions.
    """

    _KEYWORD_FIELDS = ["keywords_ar", "keywords_arabizi", "keywords_fr"]

    def __init__(self, db: DatabaseManager) -> None:
        """Initialise le catalogue et crée la table si nécessaire.

        Args:
            db: Gestionnaire de base de données SQLite.
        """
        self._db = db
        db.execute(_DDL_PRODUCTS)
        db.commit()

    def create(
        self,
        brand: str,
        product_name: str,
        product_line: str = "",
        sku: Optional[str] = None,
        category: str = "",
        keywords_ar: list = None,
        keywords_arabizi: list = None,
        keywords_fr: list = None,
        is_active: bool = True,
    ) -> int:
        """Crée un nouveau produit dans le catalogue.

        Args:
            brand: Nom de la marque (ex: "Ramy").
            product_name: Nom du produit (ex: "Jus d'orange").
            product_line: Gamme de produit (ex: "Premium").
            sku: Code SKU unique. None si non applicable.
            category: Catégorie (ex: "jus", "nectar").
            keywords_ar: Mots-clés en arabe.
            keywords_arabizi: Mots-clés en arabizi.
            keywords_fr: Mots-clés en français.
            is_active: Produit actif (True par défaut).

        Returns:
            ID du produit créé.
        """
        cur = self._db.execute(
            """INSERT INTO products
               (brand, product_line, product_name, sku, category,
                keywords_ar, keywords_arabizi, keywords_fr, is_active)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                brand,
                product_line or "",
                product_name,
                sku,
                category or "",
                _json_encode(keywords_ar or []),
                _json_encode(keywords_arabizi or []),
                _json_encode(keywords_fr or []),
                1 if is_active else 0,
            ),
        )
        self._db.commit()
        logger.debug("Produit créé : %s (id=%d)", product_name, cur.lastrowid)
        return cur.lastrowid

    def get(self, product_id: int) -> Optional[dict]:
        """Récupère un produit par son ID.

        Args:
            product_id: Identifiant du produit.

        Returns:
            Dictionnaire du produit ou None si introuvable.
        """
        row = self._db.execute(
            "SELECT * FROM products WHERE product_id = ?", (product_id,)
        ).fetchone()
        return _decode_keywords(_row_to_dict(row), self._KEYWORD_FIELDS)

    def list(
        self,
        brand: Optional[str] = None,
        category: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> list[dict]:
        """Liste les produits avec filtres optionnels.

        Args:
            brand: Filtrer par marque (ex: "Ramy").
            category: Filtrer par catégorie.
            is_active: Filtrer par état actif/inactif.

        Returns:
            Liste de dictionnaires produits.
        """
        conditions = []
        params = []
        if brand is not None:
            conditions.append("brand = ?")
            params.append(brand)
        if category is not None:
            conditions.append("category = ?")
            params.append(category)
        if is_active is not None:
            conditions.append("is_active = ?")
            params.append(1 if is_active else 0)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        rows = self._db.execute(
            f"SELECT * FROM products {where} ORDER BY product_id", tuple(params)
        ).fetchall()
        return [
            _decode_keywords(_row_to_dict(r), self._KEYWORD_FIELDS) for r in rows
        ]

    def update(self, product_id: int, **fields) -> bool:
        """Met à jour les champs d'un produit existant.

        Args:
            product_id: Identifiant du produit à modifier.
            **fields: Champs à mettre à jour (brand, product_name, keywords_ar, etc.).

        Returns:
            True si la mise à jour a affecté une ligne, False sinon.
        """
        if not fields:
            return False

        # Encoder les champs JSON avant mise à jour
        for kw_field in self._KEYWORD_FIELDS:
            if kw_field in fields and isinstance(fields[kw_field], list):
                fields[kw_field] = _json_encode(fields[kw_field])
        if "is_active" in fields and isinstance(fields["is_active"], bool):
            fields["is_active"] = 1 if fields["is_active"] else 0

        set_clause = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [product_id]
        cur = self._db.execute(
            f"UPDATE products SET {set_clause} WHERE product_id = ?", tuple(values)
        )
        self._db.commit()
        return cur.rowcount > 0

    def delete(self, product_id: int) -> bool:
        """Supprime un produit du catalogue.

        Args:
            product_id: Identifiant du produit à supprimer.

        Returns:
            True si supprimé, False si introuvable.
        """
        cur = self._db.execute(
            "DELETE FROM products WHERE product_id = ?", (product_id,)
        )
        self._db.commit()
        return cur.rowcount > 0

    def search_by_keyword(self, keyword: str) -> list[dict]:
        """Recherche des produits par mot-clé dans tous les scripts.

        Recherche insensible à la casse dans product_name, brand,
        keywords_ar, keywords_arabizi et keywords_fr.

        Args:
            keyword: Mot-clé à rechercher (arabe, arabizi ou français).

        Returns:
            Liste des produits correspondants.
        """
        kw = f"%{keyword.lower()}%"
        rows = self._db.execute(
            """SELECT * FROM products
               WHERE lower(product_name) LIKE ?
                  OR lower(brand) LIKE ?
                  OR lower(keywords_ar) LIKE ?
                  OR lower(keywords_arabizi) LIKE ?
                  OR lower(keywords_fr) LIKE ?
               ORDER BY product_id""",
            (kw, kw, kw, kw, kw),
        ).fetchall()
        return [
            _decode_keywords(_row_to_dict(r), self._KEYWORD_FIELDS) for r in rows
        ]


# ---------------------------------------------------------------------------
# WilayaCatalog
# ---------------------------------------------------------------------------

class WilayaCatalog:
    """Catalogue des 58 wilayas algériennes avec CRUD et recherche multi-script.

    Référence géographique utilisée par l'Entity Resolver pour localiser
    les mentions. Peut être initialisé depuis data/seed/wilayas.json.
    """

    _KEYWORD_FIELDS = ["keywords_arabizi"]

    def __init__(self, db: DatabaseManager) -> None:
        """Initialise le catalogue et crée la table si nécessaire.

        Args:
            db: Gestionnaire de base de données SQLite.
        """
        self._db = db
        db.execute(_DDL_WILAYAS)
        db.commit()

    def seed_from_file(self, path: Optional[Path] = None) -> int:
        """Charge les wilayas depuis le fichier JSON de seed.

        Utilise INSERT OR IGNORE pour éviter les doublons lors d'appels
        répétés. Le chemin par défaut est data/seed/wilayas.json.

        Args:
            path: Chemin optionnel vers un fichier JSON alternatif.

        Returns:
            Nombre de wilayas insérées (0 si déjà présentes).
        """
        seed_path = path or _SEED_WILAYAS_PATH
        with open(seed_path, encoding="utf-8") as f:
            wilayas = json.load(f)

        before = self._db.execute("SELECT COUNT(*) FROM wilayas").fetchone()[0]
        self._db.executemany(
            """INSERT OR IGNORE INTO wilayas
               (wilaya_code, name_fr, name_ar, keywords_arabizi, region)
               VALUES (?, ?, ?, ?, ?)""",
            [
                (
                    w["code"],
                    w["name_fr"],
                    w.get("name_ar", ""),
                    _json_encode(w.get("keywords_arabizi", [])),
                    w.get("region", ""),
                )
                for w in wilayas
            ],
        )
        self._db.commit()
        after = self._db.execute("SELECT COUNT(*) FROM wilayas").fetchone()[0]
        inserted = after - before
        logger.info("Seed wilayas : %d insérées (%d au total)", inserted, after)
        return inserted

    def create(
        self,
        wilaya_code: str,
        name_fr: str,
        name_ar: str = "",
        keywords_arabizi: list = None,
        region: str = "",
    ) -> str:
        """Crée une wilaya dans le catalogue.

        Args:
            wilaya_code: Code officiel (ex: "06" pour Béjaïa).
            name_fr: Nom officiel en français.
            name_ar: Nom officiel en arabe.
            keywords_arabizi: Variantes arabizi courantes.
            region: Région (Centre, Est, Ouest, Sud).

        Returns:
            Code de la wilaya créée.
        """
        self._db.execute(
            """INSERT INTO wilayas
               (wilaya_code, name_fr, name_ar, keywords_arabizi, region)
               VALUES (?, ?, ?, ?, ?)""",
            (
                wilaya_code,
                name_fr,
                name_ar or "",
                _json_encode(keywords_arabizi or []),
                region or "",
            ),
        )
        self._db.commit()
        logger.debug("Wilaya créée : %s (%s)", wilaya_code, name_fr)
        return wilaya_code

    def get(self, wilaya_code: str) -> Optional[dict]:
        """Récupère une wilaya par son code officiel.

        Args:
            wilaya_code: Code officiel de la wilaya.

        Returns:
            Dictionnaire de la wilaya ou None si introuvable.
        """
        row = self._db.execute(
            "SELECT * FROM wilayas WHERE wilaya_code = ?", (wilaya_code,)
        ).fetchone()
        return _decode_keywords(_row_to_dict(row), self._KEYWORD_FIELDS)

    def list(self, region: Optional[str] = None) -> list[dict]:
        """Liste les wilayas avec filtre optionnel par région.

        Args:
            region: Filtrer par région (Centre, Est, Ouest, Sud).

        Returns:
            Liste de dictionnaires wilayas.
        """
        if region is not None:
            rows = self._db.execute(
                "SELECT * FROM wilayas WHERE region = ? ORDER BY wilaya_code",
                (region,),
            ).fetchall()
        else:
            rows = self._db.execute(
                "SELECT * FROM wilayas ORDER BY wilaya_code"
            ).fetchall()
        return [
            _decode_keywords(_row_to_dict(r), self._KEYWORD_FIELDS) for r in rows
        ]

    def update(self, wilaya_code: str, **fields) -> bool:
        """Met à jour les champs d'une wilaya existante.

        Args:
            wilaya_code: Code officiel de la wilaya à modifier.
            **fields: Champs à mettre à jour.

        Returns:
            True si la mise à jour a affecté une ligne, False sinon.
        """
        if not fields:
            return False

        if "keywords_arabizi" in fields and isinstance(
            fields["keywords_arabizi"], list
        ):
            fields["keywords_arabizi"] = _json_encode(fields["keywords_arabizi"])

        set_clause = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [wilaya_code]
        cur = self._db.execute(
            f"UPDATE wilayas SET {set_clause} WHERE wilaya_code = ?", tuple(values)
        )
        self._db.commit()
        return cur.rowcount > 0

    def delete(self, wilaya_code: str) -> bool:
        """Supprime une wilaya du catalogue.

        Args:
            wilaya_code: Code officiel de la wilaya à supprimer.

        Returns:
            True si supprimée, False si introuvable.
        """
        cur = self._db.execute(
            "DELETE FROM wilayas WHERE wilaya_code = ?", (wilaya_code,)
        )
        self._db.commit()
        return cur.rowcount > 0

    def search_by_keyword(self, keyword: str) -> list[dict]:
        """Recherche des wilayas par mot-clé dans tous les scripts.

        Recherche dans name_fr, name_ar et keywords_arabizi.

        Args:
            keyword: Mot-clé à rechercher.

        Returns:
            Liste des wilayas correspondantes.
        """
        kw = f"%{keyword.lower()}%"
        rows = self._db.execute(
            """SELECT * FROM wilayas
               WHERE lower(name_fr) LIKE ?
                  OR lower(name_ar) LIKE ?
                  OR lower(keywords_arabizi) LIKE ?
               ORDER BY wilaya_code""",
            (kw, kw, kw),
        ).fetchall()
        return [
            _decode_keywords(_row_to_dict(r), self._KEYWORD_FIELDS) for r in rows
        ]


# ---------------------------------------------------------------------------
# CompetitorCatalog
# ---------------------------------------------------------------------------

class CompetitorCatalog:
    """Catalogue des marques concurrentes avec CRUD et recherche multi-script.

    Référence utilisée par l'Entity Resolver pour identifier les mentions
    de concurrents dans les données sociales analysées.
    """

    _KEYWORD_FIELDS = ["keywords_ar", "keywords_arabizi", "keywords_fr"]

    def __init__(self, db: DatabaseManager) -> None:
        """Initialise le catalogue et crée la table si nécessaire.

        Args:
            db: Gestionnaire de base de données SQLite.
        """
        self._db = db
        db.execute(_DDL_COMPETITORS)
        db.commit()

    def create(
        self,
        brand_name: str,
        category: str = "",
        keywords_ar: list = None,
        keywords_arabizi: list = None,
        keywords_fr: list = None,
        is_active: bool = True,
    ) -> int:
        """Crée un concurrent dans le catalogue.

        Args:
            brand_name: Nom de la marque concurrente (ex: "Ifri", "Hamoud").
            category: Catégorie de produit (ex: "eau", "jus", "soda").
            keywords_ar: Mots-clés en arabe.
            keywords_arabizi: Mots-clés en arabizi.
            keywords_fr: Mots-clés en français.
            is_active: Concurrent actif (True par défaut).

        Returns:
            ID du concurrent créé.
        """
        cur = self._db.execute(
            """INSERT INTO competitors
               (brand_name, category, keywords_ar, keywords_arabizi,
                keywords_fr, is_active)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                brand_name,
                category or "",
                _json_encode(keywords_ar or []),
                _json_encode(keywords_arabizi or []),
                _json_encode(keywords_fr or []),
                1 if is_active else 0,
            ),
        )
        self._db.commit()
        logger.debug("Concurrent créé : %s (id=%d)", brand_name, cur.lastrowid)
        return cur.lastrowid

    def get(self, competitor_id: int) -> Optional[dict]:
        """Récupère un concurrent par son ID.

        Args:
            competitor_id: Identifiant du concurrent.

        Returns:
            Dictionnaire du concurrent ou None si introuvable.
        """
        row = self._db.execute(
            "SELECT * FROM competitors WHERE competitor_id = ?", (competitor_id,)
        ).fetchone()
        return _decode_keywords(_row_to_dict(row), self._KEYWORD_FIELDS)

    def list(
        self,
        category: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> list[dict]:
        """Liste les concurrents avec filtres optionnels.

        Args:
            category: Filtrer par catégorie.
            is_active: Filtrer par état actif/inactif.

        Returns:
            Liste de dictionnaires concurrents.
        """
        conditions = []
        params = []
        if category is not None:
            conditions.append("category = ?")
            params.append(category)
        if is_active is not None:
            conditions.append("is_active = ?")
            params.append(1 if is_active else 0)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        rows = self._db.execute(
            f"SELECT * FROM competitors {where} ORDER BY competitor_id", tuple(params)
        ).fetchall()
        return [
            _decode_keywords(_row_to_dict(r), self._KEYWORD_FIELDS) for r in rows
        ]

    def update(self, competitor_id: int, **fields) -> bool:
        """Met à jour les champs d'un concurrent existant.

        Args:
            competitor_id: Identifiant du concurrent à modifier.
            **fields: Champs à mettre à jour.

        Returns:
            True si la mise à jour a affecté une ligne, False sinon.
        """
        if not fields:
            return False

        for kw_field in self._KEYWORD_FIELDS:
            if kw_field in fields and isinstance(fields[kw_field], list):
                fields[kw_field] = _json_encode(fields[kw_field])
        if "is_active" in fields and isinstance(fields["is_active"], bool):
            fields["is_active"] = 1 if fields["is_active"] else 0

        set_clause = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [competitor_id]
        cur = self._db.execute(
            f"UPDATE competitors SET {set_clause} WHERE competitor_id = ?",
            tuple(values),
        )
        self._db.commit()
        return cur.rowcount > 0

    def delete(self, competitor_id: int) -> bool:
        """Supprime un concurrent du catalogue.

        Args:
            competitor_id: Identifiant du concurrent à supprimer.

        Returns:
            True si supprimé, False si introuvable.
        """
        cur = self._db.execute(
            "DELETE FROM competitors WHERE competitor_id = ?", (competitor_id,)
        )
        self._db.commit()
        return cur.rowcount > 0

    def search_by_keyword(self, keyword: str) -> list[dict]:
        """Recherche des concurrents par mot-clé dans tous les scripts.

        Recherche dans brand_name, keywords_ar, keywords_arabizi et keywords_fr.

        Args:
            keyword: Mot-clé à rechercher (arabe, arabizi ou français).

        Returns:
            Liste des concurrents correspondants.
        """
        kw = f"%{keyword.lower()}%"
        rows = self._db.execute(
            """SELECT * FROM competitors
               WHERE lower(brand_name) LIKE ?
                  OR lower(keywords_ar) LIKE ?
                  OR lower(keywords_arabizi) LIKE ?
                  OR lower(keywords_fr) LIKE ?
               ORDER BY competitor_id""",
            (kw, kw, kw, kw),
        ).fetchall()
        return [
            _decode_keywords(_row_to_dict(r), self._KEYWORD_FIELDS) for r in rows
        ]
