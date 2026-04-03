"""Generation de reponses analytiques pour le chat RAG RamyPulse."""

from __future__ import annotations

import json
import logging
import os
import re
import time

import ollama
import requests

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAYS = (1, 2, 4)
_CONFIDENCE_HIGH_THRESHOLD = 0.7
_CONFIDENCE_MEDIUM_THRESHOLD = 0.4
_TIMEOUT_SECONDS = 180

_ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
_OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
_GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models"
_ANTHROPIC_VERSION_HEADER = "2023-06-01"

_DEFAULT_MODELS = {
    "ollama_local": "llama3.2:3b",
    "google_gemini": "gemini-2.5-flash",
    "openai": "gpt-4o",
    "anthropic": "claude-opus-4-6",
}

_SYSTEM_PROMPT = (
    "Tu es un analyste de sentiment pour la marque Ramy. "
    "Reponds UNIQUEMENT a partir des extraits fournis. "
    "Cite les sources entre crochets [Source N]. "
    "Si pas assez d'info, dis-le. "
    "Reponds en francais. "
    "Reponds OBLIGATOIREMENT en JSON avec ce format exact : "
    '{"answer": "...", "sources": [1, 2, ...], "confidence": "high|medium|low"}'
)

_FALLBACK_NO_INFO = {
    "answer": "Je n'ai pas assez d'informations dans les donnees analysees.",
    "sources": [],
    "confidence": "low",
}


def _resolve_backend() -> tuple[str, str, str | None]:
    """Choisit le provider, le modele et la cle API eventuelle."""
    try:
        import config
    except ImportError:  # pragma: no cover
        config = None

    provider = (
        os.getenv("RAG_GENERATOR_PROVIDER")
        or getattr(config, "RAG_GENERATOR_PROVIDER", "")
        or "ollama_local"
    )

    model = (
        os.getenv("RAG_GENERATOR_MODEL")
        or getattr(config, "RAG_GENERATOR_MODEL", "")
        or (
            getattr(config, "OLLAMA_MODEL", _DEFAULT_MODELS["ollama_local"])
            if provider == "ollama_local"
            else _DEFAULT_MODELS.get(provider, _DEFAULT_MODELS["ollama_local"])
        )
    )

    api_key = None
    if provider == "google_gemini":
        api_key = os.getenv("GOOGLE_API_KEY") or getattr(config, "GOOGLE_API_KEY", "")
    elif provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY") or getattr(config, "OPENAI_API_KEY", "")
    elif provider == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY") or getattr(config, "ANTHROPIC_API_KEY", "")

    return provider, model, api_key or None


class Generator:
    """Genere des reponses RAG en utilisant Ollama ou un provider API."""

    @staticmethod
    def describe_backend() -> str:
        """Retourne un libelle humain du backend actif."""
        provider, model, _ = _resolve_backend()
        mapping = {
            "ollama_local": "Ollama local",
            "google_gemini": "Google Gemini",
            "openai": "OpenAI",
            "anthropic": "Anthropic Claude",
        }
        return f"{mapping.get(provider, provider)} ({model})"

    def generate(self, question: str, chunks: list[dict]) -> dict:
        """Genere une reponse analytique a partir d'une question et de chunks."""
        if not chunks:
            logger.info("Aucun chunk fourni - reponse fallback.")
            return dict(_FALLBACK_NO_INFO)

        extraits = "\n".join(
            f"[Source {i + 1}] (canal: {c['channel']}) {c['text']}"
            for i, c in enumerate(chunks)
        )
        user_msg = f"Question: {question}\n\nExtraits:\n{extraits}"
        provider, model, api_key = _resolve_backend()

        last_exc: Exception | None = None
        for attempt in range(MAX_RETRIES):
            try:
                raw = self._call_provider(
                    provider=provider,
                    model=model,
                    api_key=api_key,
                    user_msg=user_msg,
                )
                return self._parse(raw, chunks)
            except Exception as exc:
                last_exc = exc
                if attempt < MAX_RETRIES - 1:
                    delay = RETRY_DELAYS[attempt]
                    logger.warning(
                        "Tentative %d/%d echouee sur %s (%s) - reessai dans %ds.",
                        attempt + 1,
                        MAX_RETRIES,
                        provider,
                        exc,
                        delay,
                    )
                    time.sleep(delay)

        logger.error("Erreur generation apres %d tentatives : %s", MAX_RETRIES, last_exc)
        return self._fallback_with_source(chunks)

    @staticmethod
    def _call_provider(provider: str, model: str, api_key: str | None, user_msg: str) -> str:
        """Appelle le provider actif et retourne le texte brut JSON."""
        if provider == "ollama_local":
            response = ollama.chat(
                model=model,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
            )
            return response["message"]["content"]

        if provider == "google_gemini":
            if not api_key:
                raise ValueError("GOOGLE_API_KEY manquante pour le chat RAG")
            response = requests.post(
                f"{_GEMINI_API_URL}/{model}:generateContent",
                headers={"Content-Type": "application/json"},
                params={"key": api_key},
                json={
                    "system_instruction": {"parts": [{"text": _SYSTEM_PROMPT}]},
                    "contents": [{"parts": [{"text": user_msg}]}],
                    "generationConfig": {
                        "maxOutputTokens": 2048,
                        "responseMimeType": "application/json",
                        "thinkingConfig": {"thinkingBudget": 0},
                    },
                },
                timeout=_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            return response.json()["candidates"][0]["content"]["parts"][0]["text"]

        if provider == "openai":
            if not api_key:
                raise ValueError("OPENAI_API_KEY manquante pour le chat RAG")
            response = requests.post(
                _OPENAI_API_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": _SYSTEM_PROMPT},
                        {"role": "user", "content": user_msg},
                    ],
                    "max_tokens": 2048,
                },
                timeout=_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]

        if provider == "anthropic":
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY manquante pour le chat RAG")
            response = requests.post(
                _ANTHROPIC_API_URL,
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": _ANTHROPIC_VERSION_HEADER,
                    "content-type": "application/json",
                },
                json={
                    "model": model,
                    "max_tokens": 2048,
                    "system": _SYSTEM_PROMPT,
                    "messages": [{"role": "user", "content": user_msg}],
                },
                timeout=_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            return response.json()["content"][0]["text"]

        raise ValueError(f"Provider RAG non supporte: {provider}")

    @staticmethod
    def _extract_json(raw: str) -> dict | None:
        """Extrait un objet JSON depuis une chaine brute."""
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            pass

        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except (json.JSONDecodeError, ValueError):
                pass

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
        """Calcule le niveau de confiance base sur la similarite des chunks."""
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
        """Parse la reponse JSON et valide les indices de sources."""
        data = self._extract_json(raw)
        if data is None:
            logger.warning("Reponse LLM non-JSON : %.80s...", raw)
            return self._fallback_with_source(chunks)

        answer = str(data.get("answer", ""))
        confidence = self._compute_confidence(chunks)

        sources = []
        for src in data.get("sources", []):
            try:
                idx = int(src) - 1
                if 0 <= idx < len(chunks):
                    chunk = chunks[idx]
                    sources.append(
                        {
                            "text": chunk.get("text", ""),
                            "channel": chunk.get("channel", ""),
                            "url": chunk.get("url", ""),
                            "timestamp": chunk.get("timestamp", ""),
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
