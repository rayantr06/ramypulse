"""Index FAISS HNSW avec metadata JSON pour RamyPulse.

Stratégie PoC : add() recrée l'index complet à chaque appel.
Sauvegarde en deux fichiers : {path}.faiss + {path}.json.
"""
import json
import logging
import os

import faiss
import numpy as np

logger = logging.getLogger(__name__)

_DIM = 768
_HNSW_M = 32  # connexions par nœud HNSW


class VectorStore:
    """Index FAISS HNSW avec metadata associée, persistable sur disque."""

    def __init__(self) -> None:
        """Initialise un index HNSW vide."""
        self.index: faiss.IndexHNSWFlat = faiss.IndexHNSWFlat(_DIM, _HNSW_M)
        self.metadata: list[dict] = []

    @property
    def ntotal(self) -> int:
        """Retourne le nombre réel de vecteurs présents dans l'index."""
        return int(self.index.ntotal)

    def add(self, vectors: np.ndarray, metadata_list: list[dict]) -> None:
        """Recrée l'index et ajoute les vecteurs avec leur metadata.

        Remplace intégralement l'index existant (pas d'accumulation).

        Args:
            vectors: Matrice float32 (n, 768) de vecteurs normalisés L2.
            metadata_list: Liste de n dicts (text, channel, source_url, timestamp…).
        """
        self.index = faiss.IndexHNSWFlat(_DIM, _HNSW_M)
        self.metadata = list(metadata_list)

        if len(vectors) > 0:
            vecs = np.array(vectors, dtype=np.float32)
            self.index.add(vecs)
            logger.info("VectorStore : %d vecteurs indexés.", self.index.ntotal)

    def add_incremental(self, vectors: np.ndarray, metadata_list: list[dict]) -> None:
        """Ajoute des vecteurs à l'index existant sans le reconstruire.

        Args:
            vectors: Matrice de shape (n, 768) convertible en float32.
            metadata_list: Liste de n métadonnées associées aux vecteurs.

        Raises:
            ValueError: Si la dimension des vecteurs ou la cardinalité diffèrent.
        """
        vecs = np.asarray(vectors, dtype=np.float32)
        if vecs.ndim != 2 or vecs.shape[1] != _DIM:
            raise ValueError(f"vectors doit être de shape (n, {_DIM}).")
        if vecs.shape[0] != len(metadata_list):
            raise ValueError("vectors et metadata_list doivent avoir la même longueur.")

        if vecs.shape[0] == 0:
            logger.info(
                "VectorStore : 0 vecteur ajouté en incrémental (%d total).",
                self.ntotal,
            )
            return

        self.index.add(vecs)
        self.metadata.extend(metadata_list)
        logger.info(
            "VectorStore : %d vecteurs ajoutés en incrémental (%d total).",
            vecs.shape[0],
            self.ntotal,
        )

    def search(self, query_vec: np.ndarray, k: int) -> list[tuple[dict, float, int]]:
        """Recherche les k voisins les plus proches par distance L2.

        Args:
            query_vec: Vecteur requête float32 de shape (1, 768) ou (768,).
            k: Nombre maximum de résultats.

        Returns:
            Liste de (metadata_dict, distance_l2, index_positionnel)
            triée du plus proche au plus loin.
        """
        if self.index.ntotal == 0:
            return []

        q = np.array(query_vec, dtype=np.float32)
        if q.ndim == 1:
            q = q.reshape(1, -1)

        k_actual = min(k, self.index.ntotal)
        distances, indices = self.index.search(q, k_actual)

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            pos = int(idx)
            if 0 <= pos < len(self.metadata):
                results.append((self.metadata[pos], float(dist), pos))
        return results

    def save(self, path: str) -> None:
        """Sauvegarde l'index FAISS et la metadata sur disque.

        Crée {path}.faiss et {path}.json.

        Args:
            path: Chemin de base sans extension.
        """
        parent = os.path.dirname(os.path.abspath(path))
        os.makedirs(parent, exist_ok=True)
        faiss.write_index(self.index, f"{path}.faiss")
        with open(f"{path}.json", "w", encoding="utf-8") as fh:
            json.dump(self.metadata, fh, ensure_ascii=False, indent=2)
        logger.info("VectorStore sauvegardé : %s (.faiss + .json)", path)

    @classmethod
    def load(cls, path: str) -> "VectorStore":
        """Charge l'index FAISS et la metadata depuis le disque.

        Args:
            path: Chemin de base sans extension (doit exister .faiss + .json).

        Returns:
            Instance VectorStore prête à l'emploi.
        """
        vs = cls()
        vs.index = faiss.read_index(f"{path}.faiss")
        with open(f"{path}.json", "r", encoding="utf-8") as fh:
            vs.metadata = json.load(fh)
        logger.info("VectorStore chargé : %d vecteurs.", vs.index.ntotal)
        return vs
