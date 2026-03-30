"""Entity Resolver v1 déterministe pour RamyPulse.

Enrichit les mentions textuelles avec les dimensions métier Phase 1 :
brand, product, product_line, sku, wilaya, competitor.

Approche : dictionnaires stricts multi-script (arabe / arabizi / français).
Précision > rappel — champ laissé à None si ambiguïté.
Pas de NER ML dans cette version.

Dépendances : core/business_catalog.py, core/database.py.
"""
from __future__ import annotations

import logging
import re
from typing import NamedTuple

import pandas as pd

# Limite minimale de longueur pour le matching par sous-chaîne.
# Les keywords plus courts exigent un matching mot-entier (word boundary)
# pour éviter les faux positifs (ex: "to" dans "partout").
_MIN_SUBSTRING_LEN = 4

# Pattern de bornes de mot multi-script (Latin + Arabe)
_NON_WORD_CHAR = r"[a-zA-Z0-9\u0600-\u06FF]"

from core.business_catalog import CompetitorCatalog, ProductCatalog, WilayaCatalog
from core.database import DatabaseManager

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Structures internes de l'index
# ---------------------------------------------------------------------------

class _ProductEntry(NamedTuple):
    """Entrée dans l'index produit.

    Attributes:
        keyword: Mot-clé en minuscules.
        specificity: 2 = keyword produit, 1 = keyword marque seulement.
        product_id: Identifiant interne du produit.
        brand: Nom de la marque.
        product_name: Nom du produit.
        product_line: Gamme (peut être vide).
        sku: Code SKU (peut être None).
    """

    keyword: str
    specificity: int
    product_id: str
    brand: str
    product_name: str
    product_line: str
    sku: str | None


class _WilayaEntry(NamedTuple):
    """Entrée dans l'index wilaya.

    Attributes:
        keyword: Mot-clé en minuscules.
        wilaya_code: Code officiel de la wilaya.
        name_fr: Nom en français (pour les logs).
    """

    keyword: str
    wilaya_code: str
    wilaya_name_fr: str


class _CompetitorEntry(NamedTuple):
    """Entrée dans l'index concurrent.

    Attributes:
        keyword: Mot-clé en minuscules.
        competitor_id: Identifiant interne.
        brand_name: Nom de la marque concurrente.
    """

    keyword: str
    competitor_id: str
    brand_name: str


# ---------------------------------------------------------------------------
# EntityResolver
# ---------------------------------------------------------------------------

class EntityResolver:
    """Résolveur d'entités métier v1 pour RamyPulse.

    Construit des indices de recherche à l'initialisation puis les
    réutilise pour toutes les résolutions (sans requêtes SQL répétées).

    Exemple :
        db = DatabaseManager(":memory:")
        resolver = EntityResolver(db)
        result = resolver.resolve_text("jus orange ramy trop bon")
        # → {"brand": "Ramy", "product": "Jus Orange", ...}
    """

    def __init__(self, db: DatabaseManager) -> None:
        """Initialise le resolver et construit les indices de recherche.

        Les indices sont construits une seule fois à l'initialisation.
        Tout changement de catalogue nécessite de recréer l'instance.

        Args:
            db: Gestionnaire de base de données SQLite avec les catalogues.
        """
        self._db = db
        self._build_indices()
        logger.debug(
            "EntityResolver initialisé — %d entrées produit, %d wilaya, %d concurrent",
            len(self._product_index),
            len(self._wilaya_index),
            len(self._competitor_index),
        )

    # ------------------------------------------------------------------
    # Construction des indices
    # ------------------------------------------------------------------

    def _build_indices(self) -> None:
        """Construit les trois indices de recherche depuis les catalogues SQLite.

        Trie chaque index par longueur de keyword décroissante pour que le
        matching longest-first soit respecté lors des itérations.
        """
        self._product_index: list[_ProductEntry] = self._build_product_index()
        self._wilaya_index: list[_WilayaEntry] = self._build_wilaya_index()
        self._competitor_index: list[_CompetitorEntry] = self._build_competitor_index()

    def _build_product_index(self) -> list[_ProductEntry]:
        """Construit l'index des mots-clés produits depuis ProductCatalog.

        Returns:
            Liste triée par longueur de keyword décroissante.
        """
        catalog = ProductCatalog(self._db)
        entries: list[_ProductEntry] = []

        for p in catalog.list(is_active=True):
            pid = p["product_id"]
            brand = p["brand"] or ""
            product_name = p["product_name"] or ""
            product_line = p.get("product_line") or ""
            sku = p.get("sku")

            def _add(kw: str, spec: int) -> None:
                kw_clean = (kw or "").strip().lower()
                if kw_clean:
                    entries.append(
                        _ProductEntry(kw_clean, spec, pid, brand, product_name, product_line, sku)
                    )

            # Spécificité 2 : keyword directement lié au produit
            _add(product_name, 2)
            if sku:
                _add(sku, 2)
            for kw in p.get("keywords_ar") or []:
                _add(kw, 2)
            for kw in p.get("keywords_arabizi") or []:
                _add(kw, 2)
            for kw in p.get("keywords_fr") or []:
                _add(kw, 2)

            # Spécificité 1 : marque seulement
            _add(brand, 1)

        return sorted(entries, key=lambda e: len(e.keyword), reverse=True)

    def _build_wilaya_index(self) -> list[_WilayaEntry]:
        """Construit l'index des mots-clés wilayas depuis WilayaCatalog.

        Returns:
            Liste triée par longueur de keyword décroissante.
        """
        catalog = WilayaCatalog(self._db)
        entries: list[_WilayaEntry] = []

        for w in catalog.list():
            code = w["wilaya_code"]
            wilaya_name_fr = w.get("wilaya_name_fr") or ""

            def _add(kw: str) -> None:
                kw_clean = (kw or "").strip().lower()
                if kw_clean:
                    entries.append(_WilayaEntry(kw_clean, code, wilaya_name_fr))

            _add(wilaya_name_fr)
            if w.get("wilaya_name_ar"):
                _add(w["wilaya_name_ar"])
            for kw in w.get("keywords_arabizi") or []:
                _add(kw)

        return sorted(entries, key=lambda e: len(e.keyword), reverse=True)

    def _build_competitor_index(self) -> list[_CompetitorEntry]:
        """Construit l'index des mots-clés concurrents depuis CompetitorCatalog.

        Returns:
            Liste triée par longueur de keyword décroissante.
        """
        catalog = CompetitorCatalog(self._db)
        entries: list[_CompetitorEntry] = []

        for c in catalog.list(is_active=True):
            cid = c["competitor_id"]
            brand_name = c["brand_name"] or ""

            def _add(kw: str) -> None:
                kw_clean = (kw or "").strip().lower()
                if kw_clean:
                    entries.append(_CompetitorEntry(kw_clean, cid, brand_name))

            _add(brand_name)
            for kw in c.get("keywords_ar") or []:
                _add(kw)
            for kw in c.get("keywords_arabizi") or []:
                _add(kw)
            for kw in c.get("keywords_fr") or []:
                _add(kw)

        return sorted(entries, key=lambda e: len(e.keyword), reverse=True)

    # ------------------------------------------------------------------
    # API publique
    # ------------------------------------------------------------------

    def resolve_text(
        self,
        text: str | None,
        source_metadata: dict | None = None,
    ) -> dict:
        """Résout les entités métier d'un texte libre.

        Recherche déterministe basée sur les dictionnaires du catalogue.
        Précision > rappel : retourne None sur un champ ambigu plutôt
        qu'une attribution incorrecte.

        Args:
            text: Texte à analyser (arabizi, arabe, français ou mixte).
            source_metadata: Métadonnées de la source (brand, wilaya, etc.)
                             utilisées en complément si le texte ne suffit pas.

        Returns:
            Dictionnaire avec les clés :
                brand, product, product_line, sku, wilaya, competitor,
                resolution_evidence, resolution_confidence, matched_keywords.
        """
        result: dict = {
            "brand": None,
            "product": None,
            "product_line": None,
            "sku": None,
            "wilaya": None,
            "competitor": None,
            "resolution_evidence": [],
            "resolution_confidence": "none",
            "matched_keywords": [],
        }

        text_lower = (text or "").lower()

        self._resolve_product(text_lower, result)
        self._resolve_wilaya(text_lower, result)
        self._resolve_competitor(text_lower, result)

        if source_metadata:
            self._apply_source_metadata(source_metadata, result)

        # Score de confiance global
        filled = sum(
            1 for k in ("brand", "product", "wilaya", "competitor")
            if result.get(k) is not None
        )
        result["resolution_confidence"] = (
            "high" if filled >= 2 else ("medium" if filled == 1 else "none")
        )

        return result

    def enrich_dataframe(
        self,
        df: pd.DataFrame,
        source_metadata_map: dict | None = None,
    ) -> pd.DataFrame:
        """Enrichit un DataFrame avec les dimensions métier résolues.

        Ajoute les colonnes manquantes brand/product/product_line/sku/
        wilaya/competitor. Ne modifie pas le DataFrame d'entrée (copie).
        Préserve les valeurs existantes non nulles.

        Args:
            df: DataFrame d'entrée avec au moins une colonne 'text'.
            source_metadata_map: Mapping {index_ligne: dict_metadata}
                                 optionnel pour enrichir la résolution.

        Returns:
            Nouveau DataFrame enrichi des colonnes métier.
        """
        result_df = df.copy()

        _ENTITY_COLS = ("brand", "product", "product_line", "sku", "wilaya", "competitor")

        # Ajouter les colonnes absentes
        for col in _ENTITY_COLS:
            if col not in result_df.columns:
                result_df[col] = None

        # Résoudre chaque ligne
        indices = result_df.index.tolist()
        texts = result_df["text"].tolist() if "text" in result_df.columns else [""] * len(result_df)

        resolutions = []
        for i, idx in enumerate(indices):
            txt = texts[i]
            txt = str(txt) if (txt is not None and not _is_na(txt)) else ""
            meta = source_metadata_map.get(idx) if source_metadata_map else None
            resolutions.append(self.resolve_text(txt, meta))

        # Appliquer uniquement sur les cellules nulles (préserver l'existant)
        for col in _ENTITY_COLS:
            col_values = result_df[col].tolist()
            resolved_values = [r[col] for r in resolutions]
            new_values = [
                existing if not _is_na(existing) else resolved
                for existing, resolved in zip(col_values, resolved_values)
            ]
            result_df[col] = new_values

        return result_df

    # ------------------------------------------------------------------
    # Résolution interne
    # ------------------------------------------------------------------

    def _resolve_product(self, text_lower: str, result: dict) -> None:
        """Résout brand, product, product_line, sku depuis l'index produit.

        Applique la priorité : produit spécifique (spec=2) > marque seule (spec=1).
        En cas d'ambiguïté entre produits distincts, ne résout que la marque
        si elle est unique.

        Args:
            text_lower: Texte normalisé en minuscules.
            result: Dictionnaire de sortie à compléter.
        """
        if not text_lower:
            return

        # Collecter les matchs uniques par product_id
        seen_pids: set[str] = set()
        matches: list[_ProductEntry] = []
        for entry in self._product_index:
            if _keyword_in_text(entry.keyword, text_lower) and entry.product_id not in seen_pids:
                seen_pids.add(entry.product_id)
                matches.append(entry)

        if not matches:
            return

        max_spec = max(e.specificity for e in matches)
        top_matches = [e for e in matches if e.specificity == max_spec]

        if max_spec == 2:
            # Matchs spécifiques au produit
            unique_pids = {e.product_id for e in top_matches}
            if len(unique_pids) == 1:
                entry = top_matches[0]
                result["brand"] = entry.brand
                result["product"] = entry.product_name
                result["product_line"] = entry.product_line or None
                result["sku"] = entry.sku
                result["matched_keywords"].append(entry.keyword)
                result["resolution_evidence"].append(f"product:{entry.product_name}")
            else:
                # Ambiguïté produit → brand uniquement si commune
                brands = {e.brand for e in top_matches}
                if len(brands) == 1:
                    result["brand"] = next(iter(brands))
                    result["resolution_evidence"].append("brand:ambiguous_product")
        else:
            # Seuls des matchs marque (spec=1)
            brands = {e.brand for e in top_matches}
            if len(brands) == 1:
                entry = top_matches[0]
                result["brand"] = entry.brand
                result["matched_keywords"].append(entry.keyword)
                result["resolution_evidence"].append(f"brand:{entry.brand}")

    def _resolve_wilaya(self, text_lower: str, result: dict) -> None:
        """Résout la wilaya depuis l'index géographique.

        Conservateur : si deux wilayas distinctes matchent, laisse None.

        Args:
            text_lower: Texte normalisé en minuscules.
            result: Dictionnaire de sortie à compléter.
        """
        if not text_lower:
            return

        seen_codes: set[str] = set()
        matches: list[_WilayaEntry] = []
        for entry in self._wilaya_index:
            if _keyword_in_text(entry.keyword, text_lower) and entry.wilaya_code not in seen_codes:
                seen_codes.add(entry.wilaya_code)
                matches.append(entry)

        if len(matches) == 1:
            entry = matches[0]
            result["wilaya"] = entry.wilaya_code
            result["matched_keywords"].append(entry.keyword)
            result["resolution_evidence"].append(f"wilaya:{entry.wilaya_name_fr}")
        elif len(matches) > 1:
            logger.debug(
                "Ambiguïté wilaya : %s — champ laissé à None",
                [e.wilaya_name_fr for e in matches],
            )

    def _resolve_competitor(self, text_lower: str, result: dict) -> None:
        """Résout le concurrent depuis l'index concurrents.

        Conservateur : si deux concurrents matchent, laisse None.

        Args:
            text_lower: Texte normalisé en minuscules.
            result: Dictionnaire de sortie à compléter.
        """
        if not text_lower:
            return

        seen_cids: set[str] = set()
        matches: list[_CompetitorEntry] = []
        for entry in self._competitor_index:
            if _keyword_in_text(entry.keyword, text_lower) and entry.competitor_id not in seen_cids:
                seen_cids.add(entry.competitor_id)
                matches.append(entry)

        if len(matches) == 1:
            entry = matches[0]
            result["competitor"] = entry.brand_name
            result["matched_keywords"].append(entry.keyword)
            result["resolution_evidence"].append(f"competitor:{entry.brand_name}")
        elif len(matches) > 1:
            logger.debug(
                "Ambiguïté concurrent : %s — champ laissé à None",
                [e.brand_name for e in matches],
            )

    def _apply_source_metadata(self, source_metadata: dict, result: dict) -> None:
        """Complète la résolution avec les métadonnées de source en fallback.

        Ne remplace jamais une valeur déjà détectée dans le texte.

        Args:
            source_metadata: Dictionnaire de métadonnées source (brand, wilaya, etc.).
            result: Dictionnaire de sortie à compléter.
        """
        for field in ("brand", "wilaya", "competitor"):
            if result[field] is None and source_metadata.get(field):
                result[field] = source_metadata[field]
                result["resolution_evidence"].append(f"{field}:source_metadata")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _keyword_in_text(keyword: str, text_lower: str) -> bool:
    """Vérifie si un mot-clé apparaît dans un texte normalisé.

    Pour les mots-clés courts (< 4 caractères), applique un matching
    mot-entier pour éviter les faux positifs par sous-chaîne (ex: "to" dans
    "partout"). Pour les mots-clés longs, le matching par sous-chaîne suffit.

    Args:
        keyword: Mot-clé en minuscules.
        text_lower: Texte normalisé en minuscules.

    Returns:
        True si le mot-clé est trouvé dans le texte.
    """
    if keyword not in text_lower:
        return False  # Rejet rapide
    if len(keyword) >= _MIN_SUBSTRING_LEN:
        return True
    # Mot-clé court : vérifier les bornes de mot (Latin + Arabe)
    pattern = r"(?<!" + _NON_WORD_CHAR + r")" + re.escape(keyword) + r"(?!" + _NON_WORD_CHAR + r")"
    return bool(re.search(pattern, text_lower))


def _is_na(value) -> bool:
    """Retourne True si la valeur est None ou un NaN pandas/numpy.

    Args:
        value: Valeur à tester.

    Returns:
        True si la valeur est considérée manquante.
    """
    if value is None:
        return True
    try:
        import math
        if isinstance(value, float) and math.isnan(value):
            return True
    except (TypeError, ValueError):
        pass
    # Cas pandas NA
    try:
        import pandas as pd
        return pd.isna(value)
    except (TypeError, ValueError):
        return False
