"""Génération de réponses analytiques via Ollama (llama3.2:3b) pour RamyPulse.

Le générateur utilise les chunks récupérés par le Retriever pour formuler
une réponse citant les sources. La réponse Ollama est attendue en JSON.

Garde-fous actifs :
- Parsing JSON robuste (markdown-wrapped, texte autour)
- Retry avec backoff exponentiel (3 tentatives)
- Confidence calculée sur la similarité des chunks, pas l'auto-évaluation LLM
"""
import json
import logging
import re
import time

import ollama

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAYS = (1, 2, 4)  # secondes entre les tentatives, backoff exponentiel
_CONFIDENCE_HIGH_THRESHOLD = 0.7
_CONFIDENCE_MEDIUM_THRESHOLD = 0.4

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

        Tente jusqu'à MAX_RETRIES fois avec backoff exponentiel si Ollama est
        indisponible. Retourne un fallback si toutes les tentatives échouent.

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

        last_exc: Exception | None = None
        for attempt in range(MAX_RETRIES):
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
                last_exc = exc
                if attempt < MAX_RETRIES - 1:
                    delay = RETRY_DELAYS[attempt]
                    logger.warning(
                        "Tentative %d/%d échouée (%s) — réessai dans %ds.",
                        attempt + 1,
                        MAX_RETRIES,
                        exc,
                        delay,
                    )
                    time.sleep(delay)

        logger.error(
            "Erreur Ollama après %d tentatives : %s", MAX_RETRIES, last_exc
        )
        return self._fallback_with_source(chunks)

    @staticmethod
    def _extract_json(raw: str) -> dict | None:
        """Extrait un objet JSON depuis une chaîne brute, même wrappée en markdown.

        Tente dans l'ordre :
        1. json.loads() direct
        2. Extraction depuis un bloc ```json...``` ou ```...```
        3. Extraction entre le premier { et le dernier }
        4. Retourne None si tout échoue

        Args:
            raw: Chaîne brute retournée par Ollama.

        Returns:
            Dict parsé ou None si extraction impossible.
        """
        # 1. Essai direct
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            pass

        # 2. Bloc markdown ```json...``` ou ```...```
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except (json.JSONDecodeError, ValueError):
                pass

        # 3. Premier { ... dernier }
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and start < end:
            try:
                return json.loads(raw[start : end + 1])
            except (json.JSONDecodeError, ValueError):
                pass

        return None

    @staticmethod
    def _compute_confidence(chunks: list[dict]) -> str:
        """Calcule le niveau de confiance basé sur la similarité des chunks récupérés.

        Utilise le champ 'score' de chaque chunk (similarité cosine du retriever).
        Cette méthode remplace l'auto-évaluation du LLM, non fiable car le modèle
        déclare souvent 'high' même en cas d'hallucination.

        Règles :
        - Moyenne > 0.7 → "high"
        - Moyenne > 0.4 → "medium"
        - Sinon         → "low"
        - Aucun chunk avec 'score' → "medium" (neutre, données insuffisantes)

        Args:
            chunks: Chunks récupérés par le Retriever.

        Returns:
            Niveau de confiance : "high", "medium" ou "low".
        """
        scores = [c["score"] for c in chunks if "score" in c]
        if not scores:
            return "medium"
        avg = sum(scores) / len(scores)
        if avg > _CONFIDENCE_HIGH_THRESHOLD:
            return "high"
        if avg > _CONFIDENCE_MEDIUM_THRESHOLD:
            return "medium"
        return "low"

    def _parse(self, raw: str, chunks: list[dict]) -> dict:
        """Parse la réponse JSON d'Ollama et valide les indices de sources.

        Utilise _extract_json() pour un parsing robuste (markdown-wrapped, texte
        autour). La confidence est calculée par _compute_confidence() sur les
        scores de similarité des chunks, pas par l'auto-évaluation du LLM.

        Args:
            raw: Chaîne brute retournée par Ollama.
            chunks: Chunks originaux (pour résoudre les indices de sources).

        Returns:
            Dict normalisé {answer, sources, confidence}.
        """
        data = self._extract_json(raw)
        if data is None:
            logger.warning("Réponse Ollama non-JSON : %.80s…", raw)
            return self._fallback_with_source(chunks)

        answer = str(data.get("answer", ""))
        confidence = self._compute_confidence(chunks)

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
