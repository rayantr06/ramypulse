"""Catalogue metier RamyPulse : produits, wilayas, concurrents."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any
from uuid import uuid4

from core.database import DatabaseManager

logger = logging.getLogger(__name__)

_SEED_WILAYAS_PATH = Path(__file__).parent.parent / "data" / "seed" / "wilayas.json"

_DDL_PRODUCTS = """
CREATE TABLE IF NOT EXISTS products (
    product_id TEXT PRIMARY KEY,
    brand TEXT NOT NULL,
    product_line TEXT NOT NULL DEFAULT '',
    product_name TEXT NOT NULL,
    sku TEXT UNIQUE,
    category TEXT NOT NULL DEFAULT '',
    keywords_ar TEXT NOT NULL DEFAULT '[]',
    keywords_arabizi TEXT NOT NULL DEFAULT '[]',
    keywords_fr TEXT NOT NULL DEFAULT '[]',
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
"""

_DDL_WILAYAS = """
CREATE TABLE IF NOT EXISTS wilayas (
    wilaya_code TEXT PRIMARY KEY,
    wilaya_name_fr TEXT NOT NULL,
    wilaya_name_ar TEXT NOT NULL DEFAULT '',
    keywords_arabizi TEXT NOT NULL DEFAULT '[]',
    region TEXT NOT NULL DEFAULT ''
)
"""

_DDL_COMPETITORS = """
CREATE TABLE IF NOT EXISTS competitors (
    competitor_id TEXT PRIMARY KEY,
    brand_name TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL DEFAULT '',
    keywords_ar TEXT NOT NULL DEFAULT '[]',
    keywords_arabizi TEXT NOT NULL DEFAULT '[]',
    keywords_fr TEXT NOT NULL DEFAULT '[]',
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
"""


def _json_encode(value: Any) -> str:
    """Serialize une valeur Python en JSON compact."""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def _json_decode(value: str) -> Any:
    """Deserialise une chaine JSON en valeur Python."""
    if not value:
        return []
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return value


def _row_to_dict(row) -> dict | None:
    """Convertit une sqlite3.Row en dict standard."""
    if row is None:
        return None
    return dict(row)


def _decode_keywords(record: dict | None, fields: list[str]) -> dict | None:
    """Decode les champs JSON de mots-cles d'un enregistrement."""
    if record is None:
        return None
    for field in fields:
        if field in record:
            record[field] = _json_decode(record[field])
    return record


def _normalize_boolean_field(fields: dict[str, Any], name: str) -> None:
    """Convertit un bool Python en entier SQLite si present."""
    if name in fields and isinstance(fields[name], bool):
        fields[name] = 1 if fields[name] else 0


def _generate_entity_id(prefix: str) -> str:
    """Genere un identifiant textuel stable pour une entite catalogue."""
    return f"{prefix}-{uuid4().hex[:12]}"


class ProductCatalog:
    """Catalogue des produits Ramy avec CRUD et recherche multi-script."""

    _KEYWORD_FIELDS = ["keywords_ar", "keywords_arabizi", "keywords_fr"]

    def __init__(self, db: DatabaseManager) -> None:
        """Initialise le catalogue produits."""
        self._db = db
        db.execute(_DDL_PRODUCTS)
        db.commit()

    def create(
        self,
        brand: str,
        product_name: str,
        product_line: str = "",
        sku: str | None = None,
        category: str = "",
        keywords_ar: list | None = None,
        keywords_arabizi: list | None = None,
        keywords_fr: list | None = None,
        is_active: bool = True,
    ) -> str:
        """Cree un produit et retourne son identifiant textuel."""
        product_id = _generate_entity_id("prod")
        self._db.execute(
            """
            INSERT INTO products (
                product_id,
                brand,
                product_line,
                product_name,
                sku,
                category,
                keywords_ar,
                keywords_arabizi,
                keywords_fr,
                is_active
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                product_id,
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
        logger.debug("Produit cree : %s (id=%s)", product_name, product_id)
        return product_id

    def get(self, product_id: str) -> dict | None:
        """Recupere un produit par son identifiant."""
        row = self._db.execute(
            "SELECT * FROM products WHERE product_id = ?",
            (product_id,),
        ).fetchone()
        return _decode_keywords(_row_to_dict(row), self._KEYWORD_FIELDS)

    def list(
        self,
        brand: str | None = None,
        category: str | None = None,
        is_active: bool | None = None,
    ) -> list[dict]:
        """Liste les produits avec filtres optionnels."""
        conditions: list[str] = []
        params: list[Any] = []
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
            f"SELECT * FROM products {where} ORDER BY rowid",
            tuple(params),
        ).fetchall()
        return [_decode_keywords(_row_to_dict(row), self._KEYWORD_FIELDS) for row in rows]

    def update(self, product_id: str, **fields) -> bool:
        """Met a jour les champs d'un produit existant."""
        if not fields:
            return False

        for keyword_field in self._KEYWORD_FIELDS:
            if keyword_field in fields and isinstance(fields[keyword_field], list):
                fields[keyword_field] = _json_encode(fields[keyword_field])
        _normalize_boolean_field(fields, "is_active")

        set_clause = ", ".join(f"{column} = ?" for column in fields)
        values = list(fields.values()) + [product_id]
        cursor = self._db.execute(
            f"UPDATE products SET {set_clause} WHERE product_id = ?",
            tuple(values),
        )
        self._db.commit()
        return cursor.rowcount > 0

    def delete(self, product_id: str) -> bool:
        """Supprime un produit du catalogue."""
        cursor = self._db.execute(
            "DELETE FROM products WHERE product_id = ?",
            (product_id,),
        )
        self._db.commit()
        return cursor.rowcount > 0

    def search_by_keyword(self, keyword: str) -> list[dict]:
        """Recherche des produits par mot-cle dans tous les scripts."""
        like_keyword = f"%{keyword.lower()}%"
        rows = self._db.execute(
            """
            SELECT * FROM products
            WHERE lower(product_name) LIKE ?
               OR lower(brand) LIKE ?
               OR lower(keywords_ar) LIKE ?
               OR lower(keywords_arabizi) LIKE ?
               OR lower(keywords_fr) LIKE ?
            ORDER BY rowid
            """,
            (like_keyword, like_keyword, like_keyword, like_keyword, like_keyword),
        ).fetchall()
        return [_decode_keywords(_row_to_dict(row), self._KEYWORD_FIELDS) for row in rows]


class WilayaCatalog:
    """Catalogue des wilayas algeriennes avec CRUD et recherche multi-script."""

    _KEYWORD_FIELDS = ["keywords_arabizi"]

    def __init__(self, db: DatabaseManager) -> None:
        """Initialise le catalogue wilayas."""
        self._db = db
        db.execute(_DDL_WILAYAS)
        db.commit()

    def seed_from_file(self, path: Path | None = None) -> int:
        """Charge les wilayas depuis le fichier JSON de seed."""
        seed_path = path or _SEED_WILAYAS_PATH
        with open(seed_path, encoding="utf-8") as handle:
            wilayas = json.load(handle)

        before = self._db.execute("SELECT COUNT(*) FROM wilayas").fetchone()[0]
        self._db.executemany(
            """
            INSERT OR IGNORE INTO wilayas (
                wilaya_code,
                wilaya_name_fr,
                wilaya_name_ar,
                keywords_arabizi,
                region
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (
                    wilaya["code"],
                    wilaya["name_fr"],
                    wilaya.get("name_ar", ""),
                    _json_encode(wilaya.get("keywords_arabizi", [])),
                    wilaya.get("region", ""),
                )
                for wilaya in wilayas
            ],
        )
        self._db.commit()
        after = self._db.execute("SELECT COUNT(*) FROM wilayas").fetchone()[0]
        inserted = after - before
        logger.info("Seed wilayas : %d inserees (%d au total)", inserted, after)
        return inserted

    def create(
        self,
        wilaya_code: str,
        name_fr: str | None = None,
        name_ar: str = "",
        keywords_arabizi: list | None = None,
        region: str = "",
        *,
        wilaya_name_fr: str | None = None,
        wilaya_name_ar: str | None = None,
    ) -> str:
        """Cree une wilaya dans le catalogue."""
        resolved_name_fr = wilaya_name_fr if wilaya_name_fr is not None else (name_fr or "")
        resolved_name_ar = wilaya_name_ar if wilaya_name_ar is not None else (name_ar or "")
        self._db.execute(
            """
            INSERT INTO wilayas (
                wilaya_code,
                wilaya_name_fr,
                wilaya_name_ar,
                keywords_arabizi,
                region
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                wilaya_code,
                resolved_name_fr,
                resolved_name_ar,
                _json_encode(keywords_arabizi or []),
                region or "",
            ),
        )
        self._db.commit()
        logger.debug("Wilaya creee : %s (%s)", wilaya_code, resolved_name_fr)
        return wilaya_code

    def get(self, wilaya_code: str) -> dict | None:
        """Recupere une wilaya par son code."""
        row = self._db.execute(
            "SELECT * FROM wilayas WHERE wilaya_code = ?",
            (wilaya_code,),
        ).fetchone()
        return _decode_keywords(_row_to_dict(row), self._KEYWORD_FIELDS)

    def list(self, region: str | None = None) -> list[dict]:
        """Liste les wilayas avec filtre optionnel par region."""
        if region is None:
            rows = self._db.execute(
                "SELECT * FROM wilayas ORDER BY wilaya_code"
            ).fetchall()
        else:
            rows = self._db.execute(
                "SELECT * FROM wilayas WHERE region = ? ORDER BY wilaya_code",
                (region,),
            ).fetchall()
        return [_decode_keywords(_row_to_dict(row), self._KEYWORD_FIELDS) for row in rows]

    def update(self, wilaya_code: str, **fields) -> bool:
        """Met a jour les champs d'une wilaya existante."""
        if not fields:
            return False

        if "name_fr" in fields and "wilaya_name_fr" not in fields:
            fields["wilaya_name_fr"] = fields.pop("name_fr")
        if "name_ar" in fields and "wilaya_name_ar" not in fields:
            fields["wilaya_name_ar"] = fields.pop("name_ar")
        if "keywords_arabizi" in fields and isinstance(fields["keywords_arabizi"], list):
            fields["keywords_arabizi"] = _json_encode(fields["keywords_arabizi"])

        set_clause = ", ".join(f"{column} = ?" for column in fields)
        values = list(fields.values()) + [wilaya_code]
        cursor = self._db.execute(
            f"UPDATE wilayas SET {set_clause} WHERE wilaya_code = ?",
            tuple(values),
        )
        self._db.commit()
        return cursor.rowcount > 0

    def delete(self, wilaya_code: str) -> bool:
        """Supprime une wilaya du catalogue."""
        cursor = self._db.execute(
            "DELETE FROM wilayas WHERE wilaya_code = ?",
            (wilaya_code,),
        )
        self._db.commit()
        return cursor.rowcount > 0

    def search_by_keyword(self, keyword: str) -> list[dict]:
        """Recherche des wilayas par mot-cle dans tous les scripts."""
        like_keyword = f"%{keyword.lower()}%"
        rows = self._db.execute(
            """
            SELECT * FROM wilayas
            WHERE lower(wilaya_name_fr) LIKE ?
               OR lower(wilaya_name_ar) LIKE ?
               OR lower(keywords_arabizi) LIKE ?
            ORDER BY wilaya_code
            """,
            (like_keyword, like_keyword, like_keyword),
        ).fetchall()
        return [_decode_keywords(_row_to_dict(row), self._KEYWORD_FIELDS) for row in rows]


class CompetitorCatalog:
    """Catalogue des marques concurrentes avec CRUD et recherche multi-script."""

    _KEYWORD_FIELDS = ["keywords_ar", "keywords_arabizi", "keywords_fr"]

    def __init__(self, db: DatabaseManager) -> None:
        """Initialise le catalogue concurrents."""
        self._db = db
        db.execute(_DDL_COMPETITORS)
        db.commit()

    def create(
        self,
        brand_name: str,
        category: str = "",
        keywords_ar: list | None = None,
        keywords_arabizi: list | None = None,
        keywords_fr: list | None = None,
        is_active: bool = True,
    ) -> str:
        """Cree un concurrent et retourne son identifiant textuel."""
        competitor_id = _generate_entity_id("comp")
        self._db.execute(
            """
            INSERT INTO competitors (
                competitor_id,
                brand_name,
                category,
                keywords_ar,
                keywords_arabizi,
                keywords_fr,
                is_active
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                competitor_id,
                brand_name,
                category or "",
                _json_encode(keywords_ar or []),
                _json_encode(keywords_arabizi or []),
                _json_encode(keywords_fr or []),
                1 if is_active else 0,
            ),
        )
        self._db.commit()
        logger.debug("Concurrent cree : %s (id=%s)", brand_name, competitor_id)
        return competitor_id

    def get(self, competitor_id: str) -> dict | None:
        """Recupere un concurrent par son identifiant."""
        row = self._db.execute(
            "SELECT * FROM competitors WHERE competitor_id = ?",
            (competitor_id,),
        ).fetchone()
        return _decode_keywords(_row_to_dict(row), self._KEYWORD_FIELDS)

    def list(
        self,
        category: str | None = None,
        is_active: bool | None = None,
    ) -> list[dict]:
        """Liste les concurrents avec filtres optionnels."""
        conditions: list[str] = []
        params: list[Any] = []
        if category is not None:
            conditions.append("category = ?")
            params.append(category)
        if is_active is not None:
            conditions.append("is_active = ?")
            params.append(1 if is_active else 0)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        rows = self._db.execute(
            f"SELECT * FROM competitors {where} ORDER BY rowid",
            tuple(params),
        ).fetchall()
        return [_decode_keywords(_row_to_dict(row), self._KEYWORD_FIELDS) for row in rows]

    def update(self, competitor_id: str, **fields) -> bool:
        """Met a jour les champs d'un concurrent existant."""
        if not fields:
            return False

        for keyword_field in self._KEYWORD_FIELDS:
            if keyword_field in fields and isinstance(fields[keyword_field], list):
                fields[keyword_field] = _json_encode(fields[keyword_field])
        _normalize_boolean_field(fields, "is_active")

        set_clause = ", ".join(f"{column} = ?" for column in fields)
        values = list(fields.values()) + [competitor_id]
        cursor = self._db.execute(
            f"UPDATE competitors SET {set_clause} WHERE competitor_id = ?",
            tuple(values),
        )
        self._db.commit()
        return cursor.rowcount > 0

    def delete(self, competitor_id: str) -> bool:
        """Supprime un concurrent du catalogue."""
        cursor = self._db.execute(
            "DELETE FROM competitors WHERE competitor_id = ?",
            (competitor_id,),
        )
        self._db.commit()
        return cursor.rowcount > 0

    def search_by_keyword(self, keyword: str) -> list[dict]:
        """Recherche des concurrents par mot-cle dans tous les scripts."""
        like_keyword = f"%{keyword.lower()}%"
        rows = self._db.execute(
            """
            SELECT * FROM competitors
            WHERE lower(brand_name) LIKE ?
               OR lower(keywords_ar) LIKE ?
               OR lower(keywords_arabizi) LIKE ?
               OR lower(keywords_fr) LIKE ?
            ORDER BY rowid
            """,
            (like_keyword, like_keyword, like_keyword, like_keyword),
        ).fetchall()
        return [_decode_keywords(_row_to_dict(row), self._KEYWORD_FIELDS) for row in rows]
