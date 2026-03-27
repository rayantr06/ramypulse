"""Génération d'embeddings via multilingual-e5-base pour RamyPulse.

Gère les préfixes requis par le modèle E5 (query: / passage:)
et la normalisation L2 pour la recherche cosinus via FAISS.
"""
import logging

import faiss
import numpy as np

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "intfloat/multilingual-e5-base"


class Embedder:
    """Wrapper autour de multilingual-e5-base avec lazy-loading.

    Le modèle est chargé une seule fois (singleton de classe) au premier appel.
    SentenceTransformer est importé paresseusement pour éviter les conflits
    de versions torch/torchvision en environnement de test.
    """

    _model = None

    def _get_model(self):
        """Charge et met en cache le modèle SentenceTransformer.

        Returns:
            Instance SentenceTransformer prête à l'emploi.
        """
        if Embedder._model is None:
            from sentence_transformers import SentenceTransformer  # import paresseux
            try:
                import config
                model_name: str = getattr(config, "EMBEDDING_MODEL", _DEFAULT_MODEL)
            except ImportError:
                model_name = _DEFAULT_MODEL
            logger.info("Chargement du modèle d'embedding : %s", model_name)
            Embedder._model = SentenceTransformer(model_name)
        return Embedder._model

    def embed_documents(self, texts: list[str]) -> np.ndarray:
        """Génère des embeddings pour une liste de documents.

        Chaque texte est préfixé par 'passage: ' (requis par E5).

        Args:
            texts: Liste de documents à encoder.

        Returns:
            np.ndarray float32 de shape (n, 768), normalisé L2.
        """
        if not texts:
            return np.zeros((0, 768), dtype=np.float32)

        prefixed = [f"passage: {t}" for t in texts]
        model = self._get_model()
        vecs = model.encode(prefixed, convert_to_numpy=True, show_progress_bar=False)
        return self._normalize_l2(vecs.astype(np.float32))

    def embed_query(self, text: str) -> np.ndarray:
        """Génère un embedding pour une question utilisateur.

        Le texte est préfixé par 'query: ' (requis par E5).

        Args:
            text: Question à encoder.

        Returns:
            np.ndarray float32 de shape (1, 768), normalisé L2.
        """
        prefixed = [f"query: {text}"]
        model = self._get_model()
        vec = model.encode(prefixed, convert_to_numpy=True, show_progress_bar=False)
        return self._normalize_l2(vec.astype(np.float32))

    @staticmethod
    def _normalize_l2(vecs: np.ndarray) -> np.ndarray:
        """Normalise les vecteurs en norme L2 (in-place via FAISS).

        Args:
            vecs: Matrice float32 à normaliser.

        Returns:
            Même matrice avec norme L2 = 1 par ligne.
        """
        if vecs.shape[0] > 0:
            faiss.normalize_L2(vecs)
        return vecs
