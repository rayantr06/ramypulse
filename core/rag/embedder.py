"""Generation d'embeddings pour RamyPulse avec fallback robuste."""

from __future__ import annotations

import logging
import re

import faiss
import numpy as np

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "intfloat/multilingual-e5-base"


class _TransformersEmbeddingBackend:
    """Petit wrapper AutoModel/AutoTokenizer expose comme SentenceTransformer."""

    def __init__(self, tokenizer, model) -> None:
        self._tokenizer = tokenizer
        self._model = model

    def encode(
        self,
        texts: list[str],
        convert_to_numpy: bool = True,
        show_progress_bar: bool = False,
    ):
        import torch

        del show_progress_bar

        encoded = self._tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="pt",
        )
        with torch.no_grad():
            outputs = self._model(**encoded)

        token_embeddings = outputs.last_hidden_state
        attention_mask = encoded["attention_mask"].unsqueeze(-1).expand(token_embeddings.size()).float()
        masked = token_embeddings * attention_mask
        summed = masked.sum(dim=1)
        counts = attention_mask.sum(dim=1).clamp(min=1e-9)
        embeddings = summed / counts

        if convert_to_numpy:
            return embeddings.cpu().numpy()
        return embeddings


class _HashingEmbeddingBackend:
    """Fallback ultra-robuste sans dependances modeles externes."""

    def __init__(self, dim: int = 768) -> None:
        self._dim = dim

    def encode(
        self,
        texts: list[str],
        convert_to_numpy: bool = True,
        show_progress_bar: bool = False,
    ):
        del show_progress_bar

        vectors = np.zeros((len(texts), self._dim), dtype=np.float32)
        for row_index, text in enumerate(texts):
            tokens = re.findall(r"\w+", str(text).lower())
            for token in tokens:
                bucket = hash(token) % self._dim
                sign = 1.0 if (hash(f"{token}:sign") % 2 == 0) else -1.0
                vectors[row_index, bucket] += sign
        if convert_to_numpy:
            return vectors
        return vectors


class Embedder:
    """Wrapper autour de multilingual-e5-base avec lazy-loading."""

    _model = None

    def _load_sentence_transformer_model(self, model_name: str):
        """Charge SentenceTransformer quand la pile locale le permet."""
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer(model_name)

    def _load_transformers_model(self, model_name: str):
        """Fallback plus leger base sur transformers seulement."""
        from transformers import AutoModel, AutoTokenizer

        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModel.from_pretrained(model_name)
        model.eval()
        return _TransformersEmbeddingBackend(tokenizer, model)

    def _load_hashing_model(self):
        """Fallback final deterministic quand la pile HF est indisponible."""
        return _HashingEmbeddingBackend()

    def _get_model(self):
        """Charge et met en cache le backend d'embedding."""
        if Embedder._model is not None:
            return Embedder._model

        try:
            import config

            model_name: str = getattr(config, "EMBEDDING_MODEL", _DEFAULT_MODEL)
        except ImportError:
            model_name = _DEFAULT_MODEL

        logger.info("Chargement du modele d'embedding: %s", model_name)
        try:
            Embedder._model = self._load_sentence_transformer_model(model_name)
        except Exception as exc:
            logger.warning(
                "SentenceTransformer indisponible (%s). Fallback sur transformers.",
                exc,
            )
            try:
                Embedder._model = self._load_transformers_model(model_name)
            except Exception as fallback_exc:
                logger.warning(
                    "Transformers indisponible (%s). Fallback lexical local.",
                    fallback_exc,
                )
                Embedder._model = self._load_hashing_model()
        return Embedder._model

    def embed_documents(self, texts: list[str]) -> np.ndarray:
        """Genere des embeddings pour une liste de documents."""
        if not texts:
            return np.zeros((0, 768), dtype=np.float32)

        prefixed = [f"passage: {t}" for t in texts]
        model = self._get_model()
        vecs = model.encode(prefixed, convert_to_numpy=True, show_progress_bar=False)
        return self._normalize_l2(vecs.astype(np.float32))

    def embed_query(self, text: str) -> np.ndarray:
        """Genere un embedding pour une question utilisateur."""
        prefixed = [f"query: {text}"]
        model = self._get_model()
        vec = model.encode(prefixed, convert_to_numpy=True, show_progress_bar=False)
        return self._normalize_l2(vec.astype(np.float32))

    @staticmethod
    def _normalize_l2(vecs: np.ndarray) -> np.ndarray:
        """Normalise les vecteurs en norme L2."""
        if vecs.shape[0] > 0:
            faiss.normalize_L2(vecs)
        return vecs
