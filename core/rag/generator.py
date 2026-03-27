"""Génération de réponses analytiques via Ollama (llama3.2:3b) pour RamyPulse.

Le générateur utilise les chunks récupérés par le Retriever pour formuler
une réponse citant les sources. La réponse Ollama est attendue en JSON.
"""
import json
import logging

import ollama

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "Tu es un analyste de sentiment pour la marque Ramy. "
    "Réponds UNIQUEMENT à partir des extraits fournis. "
    "Cite les sources entre crochets [Source N]. "
    "Si pas assez d'info, dis-le. "
    "Réponds en français. "
    "Réponds OBLIGATOIREMENT en JSON avec ce format exact : "
    '{"answer": "...", "sources": [1, 2, ...], "confidence": "high|medium|low"}'
)

_FALLBACK_NO_INFO = {
    "answer": "Je n'ai pas assez d'informations dans les données analysées.",
    "sources": [],
    "confidence": "low",
}


class Generator:
    """Génère des réponses RAG via Ollama en se basant sur des chunks récupérés."""

    def generate(self, question: str, chunks: list[dict]) -> dict:
        """Génère une réponse analytique à partir d'une question et de chunks.

        Args:
            question: Question de l'utilisateur.
            chunks: Chunks récupérés [{text, channel, url, timestamp, score}].

        Returns:
            Dict {"answer": str, "sources": list[dict], "confidence": str}.
        """
        if not chunks:
            logger.info("Aucun chunk fourni — réponse fallback.")
            return dict(_FALLBACK_NO_INFO)

        extraits = "\n".join(
            f"[Source {i + 1}] (canal: {c['channel']}) {c['text']}"
            for i, c in enumerate(chunks)
        )
        user_msg = f"Question: {question}\n\nExtraits:\n{extraits}"

        try:
            import config
            model: str = getattr(config, "OLLAMA_MODEL", "llama3.2:3b")
        except ImportError:
            model = "llama3.2:3b"

        try:
            response = ollama.chat(
                model=model,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
            )
            raw: str = response["message"]["content"]
            return self._parse(raw, chunks)
        except Exception as exc:
            logger.error("Erreur lors de la génération Ollama : %s", exc)
            return self._fallback_with_source(chunks)

    def _parse(self, raw: str, chunks: list[dict]) -> dict:
        """Parse la réponse JSON d'Ollama et valide les indices de sources.

        Args:
            raw: Chaîne brute retournée par Ollama.
            chunks: Chunks originaux (pour résoudre les indices de sources).

        Returns:
            Dict normalisé {answer, sources, confidence}.
        """
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            logger.warning("Réponse Ollama non-JSON : %.80s…", raw)
            return self._fallback_with_source(chunks)

        answer = str(data.get("answer", ""))
        raw_confidence = data.get("confidence", "low")
        confidence = raw_confidence if raw_confidence in ("high", "medium", "low") else "low"

        # Résoudre les indices sources (1-based) en metadata de chunks
        sources = []
        for src in data.get("sources", []):
            try:
                idx = int(src) - 1  # 1-based → 0-based
                if 0 <= idx < len(chunks):
                    c = chunks[idx]
                    sources.append(
                        {
                            "text": c.get("text", ""),
                            "channel": c.get("channel", ""),
                            "url": c.get("url", ""),
                            "timestamp": c.get("timestamp", ""),
                        }
                    )
            except (ValueError, TypeError):
                continue

        if not sources:
            return self._fallback_with_source(chunks)

        if not answer.strip():
            answer = _FALLBACK_NO_INFO["answer"]

        return {"answer": answer, "sources": sources, "confidence": confidence}

    def _fallback_with_source(self, chunks: list[dict]) -> dict:
        """Construit un fallback explicite avec au moins une source si possible."""
        if not chunks:
            return dict(_FALLBACK_NO_INFO)

        source = chunks[0]
        return {
            "answer": _FALLBACK_NO_INFO["answer"],
            "sources": [
                {
                    "text": source.get("text", ""),
                    "channel": source.get("channel", ""),
                    "url": source.get("url", ""),
                    "timestamp": source.get("timestamp", ""),
                }
            ],
            "confidence": "low",
        }
