"""Moteur d'import de données pour RamyPulse.

Charge des fichiers CSV, Parquet et Excel, les valide, déduplique,
normalise les textes via le normalizer existant, et prépare un
DataFrame prêt pour le pipeline d'analyse.

Conforme au schéma Parquet enrichi du PRD §9.2.
"""
from __future__ import annotations

import hashlib
import logging
import uuid
from pathlib import Path

import pandas as pd

from core.ingestion.normalizer import normalize
from core.ingestion.validators import validate_dataframe

logger = logging.getLogger(__name__)

_SUPPORTED_EXTENSIONS = {".csv", ".parquet", ".pq", ".xlsx", ".xls"}

# Colonnes du schéma cible PRD §9.2 (pour enrichissement)
_TARGET_COLUMNS = [
    "text", "text_original", "sentiment_label", "channel", "aspect",
    "aspect_sentiments", "source_url", "timestamp", "confidence",
    "script_detected", "language", "source_registry_id", "brand",
    "competitor", "product", "product_line", "sku", "wilaya",
    "delivery_zone", "store_type", "campaign_id", "event_id",
    "creator_id", "market_segment", "ingestion_batch_id",
]


class ImportEngine:
    """Moteur d'import de fichiers pour RamyPulse.

    Supporte CSV, Parquet et Excel. Applique validation, déduplication
    et normalisation automatiquement.
    """

    def import_file(
        self,
        file_path: Path | str,
        column_mapping: dict[str, str] | None = None,
        source_registry_id: str | None = None,
        deduplicate: bool = True,
    ) -> pd.DataFrame:
        """Importe un fichier et retourne un DataFrame nettoyé.

        Args:
            file_path: Chemin vers le fichier à importer.
            column_mapping: Mapping {colonne_source: colonne_cible} optionnel.
            source_registry_id: ID de la source dans le registre (optionnel).
            deduplicate: Si True, supprime les doublons textuels.

        Returns:
            DataFrame nettoyé, validé et enrichi, prêt pour le pipeline.

        Raises:
            FileNotFoundError: Si le fichier n'existe pas.
            ValueError: Si le format n'est pas supporté, si la colonne text
                manque, ou si le fichier est vide.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Fichier introuvable : {path}")

        # Charger selon le format
        df = self._load_file(path)
        logger.info(
            "Fichier chargé : %s — %d lignes, %d colonnes.",
            path.name, len(df), len(df.columns),
        )

        # Appliquer le mapping de colonnes si fourni
        if column_mapping:
            df = self._apply_column_mapping(df, column_mapping)

        # Valider la présence de la colonne text
        if "text" not in df.columns:
            raise ValueError(
                f"Colonne 'text' manquante. "
                f"Colonnes disponibles : {list(df.columns)}. "
                f"Utilisez column_mapping pour mapper une colonne existante."
            )

        # Valider le contenu
        if len(df) == 0:
            raise ValueError(
                f"Le fichier {path.name} est vide (0 lignes de données)."
            )

        # Valider les valeurs
        errors = validate_dataframe(df)
        if errors:
            for error in errors:
                logger.warning("Validation : %s", error)

        n_before = len(df)

        # Normaliser les textes
        df = self._normalize_texts(df)

        # Dédupliquer
        if deduplicate:
            df = self._deduplicate(df)
            n_removed = n_before - len(df)
            if n_removed > 0:
                logger.info(
                    "Déduplication : %d doublons supprimés (%d → %d lignes).",
                    n_removed, n_before, len(df),
                )

        # Ajouter les métadonnées d'ingestion
        batch_id = str(uuid.uuid4())
        df["ingestion_batch_id"] = batch_id
        if source_registry_id:
            df["source_registry_id"] = source_registry_id

        # Ajouter les colonnes manquantes du schéma cible (avec None)
        for col in _TARGET_COLUMNS:
            if col not in df.columns:
                df[col] = None

        logger.info(
            "Import terminé : %d lignes prêtes (batch %s).",
            len(df), batch_id[:8],
        )
        return df

    def _load_file(self, path: Path) -> pd.DataFrame:
        """Charge un fichier selon son extension.

        Args:
            path: Chemin du fichier.

        Returns:
            DataFrame brut.

        Raises:
            ValueError: Si le format n'est pas supporté.
        """
        ext = path.suffix.lower()
        if ext not in _SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Format non supporté : '{ext}'. "
                f"Extensions acceptées : {_SUPPORTED_EXTENSIONS}"
            )

        if ext == ".csv":
            return pd.read_csv(path, encoding="utf-8")
        if ext in (".parquet", ".pq"):
            return pd.read_parquet(path)
        if ext in (".xlsx", ".xls"):
            return pd.read_excel(path)
        raise ValueError(f"Format non supporté : '{ext}'")

    def _apply_column_mapping(
        self, df: pd.DataFrame, mapping: dict[str, str]
    ) -> pd.DataFrame:
        """Renomme les colonnes selon le mapping fourni.

        Args:
            df: DataFrame à renommer.
            mapping: Dict {nom_source: nom_cible}.

        Returns:
            DataFrame avec les colonnes renommées.
        """
        rename_map = {src: tgt for src, tgt in mapping.items() if src in df.columns}
        if rename_map:
            df = df.rename(columns=rename_map)
            logger.info("Mapping de colonnes appliqué : %s", rename_map)
        return df

    def _normalize_texts(self, df: pd.DataFrame) -> pd.DataFrame:
        """Applique le normalizer sur la colonne text.

        Conserve le texte original dans text_original et remplace text
        par la version normalisée. Ajoute script_detected et language.

        Args:
            df: DataFrame avec colonne text.

        Returns:
            DataFrame avec textes normalisés et métadonnées ajoutées.
        """
        df = df.copy()

        # Sauvegarder les originaux
        df["text_original"] = df["text"].astype(str)

        normalized_texts = []
        scripts = []
        languages = []

        for text in df["text_original"]:
            result = normalize(str(text))
            normalized_texts.append(result["normalized"])
            scripts.append(result["script_detected"])
            languages.append(result["language"])

        df["text"] = normalized_texts
        df["script_detected"] = scripts
        df["language"] = languages

        return df

    def _deduplicate(self, df: pd.DataFrame) -> pd.DataFrame:
        """Supprime les doublons basés sur le hash du texte normalisé.

        Args:
            df: DataFrame avec colonne text normalisée.

        Returns:
            DataFrame sans doublons.
        """
        df = df.copy()
        df["_text_hash"] = df["text"].astype(str).str.strip().str.lower().apply(
            lambda t: hashlib.md5(t.encode("utf-8")).hexdigest()
        )
        df = df.drop_duplicates(subset=["_text_hash"], keep="first")
        df = df.drop(columns=["_text_hash"])
        return df.reset_index(drop=True)
