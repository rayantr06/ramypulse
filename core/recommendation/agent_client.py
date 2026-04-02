"""Client LLM multi-provider pour la generation de recommandations marketing.

Supporte : anthropic, openai, ollama_local.
Utilise requests (synchrone) compatible avec Streamlit.
Parse JSON robuste avec fallback si le LLM retourne du texte libre.
La cle API n'est jamais loggee.
"""

import json
import logging
import re
import time

import requests

from config import (
    ANTHROPIC_API_KEY,
    DEFAULT_AGENT_MODEL,
    DEFAULT_AGENT_PROVIDER,
    OLLAMA_BASE_URL,
    OPENAI_API_KEY,
)
from core.recommendation.prompt_manager import get_system_prompt

logger = logging.getLogger(__name__)

_ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
_OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
_ANTHROPIC_VERSION_HEADER = "2023-06-01"
_DEFAULT_MAX_TOKENS = 2000
_TIMEOUT_SECONDS = 120


# ---------------------------------------------------------------------------
# Parse JSON robuste
# ---------------------------------------------------------------------------

def _parse_json_response(raw_text: str) -> dict:
    """Parse la reponse brute du LLM en JSON avec fallback robuste.

    Tente un parse direct, puis nettoyage des fences markdown,
    puis extraction du premier bloc JSON, puis fallback structure d'erreur.

    Args:
        raw_text: Texte brut retourne par le LLM.

    Returns:
        Dict avec les cles du schema de recommandation + parse_success (bool).
    """
    def _enrich(data: dict) -> dict:
        data.setdefault("parse_success", True)
        return data

    # Tentative 1 : parse direct
    try:
        return _enrich(json.loads(raw_text))
    except json.JSONDecodeError:
        pass

    # Tentative 2 : nettoyer les fences ```json ... ```
    cleaned = re.sub(r"```json\s*|\s*```", "", raw_text, flags=re.DOTALL).strip()
    try:
        return _enrich(json.loads(cleaned))
    except json.JSONDecodeError:
        pass

    # Tentative 3 : extraire le premier bloc JSON entre { et }
    match = re.search(r"\{.*\}", raw_text, flags=re.DOTALL)
    if match:
        try:
            return _enrich(json.loads(match.group()))
        except json.JSONDecodeError:
            pass

    # Fallback : structure d'erreur exploitable
    logger.warning("Impossible de parser la reponse LLM en JSON. Retour du fallback.")
    return {
        "analysis_summary": "Erreur de parsing de la reponse agent.",
        "recommendations": [],
        "watchlist_priorities": [],
        "confidence_score": 0.0,
        "data_quality_note": f"JSON parse error — prefix: {raw_text[:200]}",
        "parse_success": False,
    }


# ---------------------------------------------------------------------------
# Construction du prompt utilisateur
# ---------------------------------------------------------------------------

def _build_user_prompt(context: dict) -> str:
    """Construit le prompt utilisateur a partir du contexte assemble.

    Args:
        context: Dict retourne par build_recommendation_context().

    Returns:
        Chaine de prompt utilisateur formatee.
    """
    client_name = context.get("client_profile", {}).get("client_name", "Ramy")
    trigger = context.get("trigger", {})
    trigger_type = trigger.get("type", "manual")
    trigger_id = trigger.get("id") or "global"

    active_alerts = context.get("active_alerts", [])
    active_watchlists = context.get("active_watchlists", [])
    recent_campaigns = context.get("recent_campaigns", [])
    rag_chunks = context.get("rag_chunks", [])
    metrics = context.get("current_metrics", {})

    return (
        f"Voici les donnees de la plateforme RamyPulse pour cette analyse :\n\n"
        f"CLIENT : {client_name}\n"
        f"DECLENCHEUR : {trigger_type} - {trigger_id}\n\n"
        f"=== METRIQUES ACTUELLES ===\n"
        f"{json.dumps(metrics, ensure_ascii=False, indent=2)}\n\n"
        f"=== ALERTES ACTIVES ({len(active_alerts)} alertes non resolues) ===\n"
        f"{json.dumps(active_alerts, ensure_ascii=False, indent=2)}\n\n"
        f"=== WATCHLISTS ACTIVES ===\n"
        f"{json.dumps(active_watchlists, ensure_ascii=False, indent=2)}\n\n"
        f"=== CAMPAGNES RECENTES ===\n"
        f"{json.dumps(recent_campaigns, ensure_ascii=False, indent=2)}\n\n"
        f"=== EXTRAITS SOURCES PERTINENTS ===\n"
        f"{json.dumps(rag_chunks, ensure_ascii=False, indent=2)}\n\n"
        "Genere les recommandations marketing les plus actionnables pour cette situation.\n"
        "Reponds UNIQUEMENT en JSON selon le format defini."
    )


# ---------------------------------------------------------------------------
# Appels providers
# ---------------------------------------------------------------------------

def _call_anthropic(api_key: str, model: str, user_prompt: str, system_prompt: str) -> dict:
    """Appelle l'API Anthropic Messages et parse la reponse JSON.

    Args:
        api_key: Cle API Anthropic (jamais loggee).
        model: Nom du modele.
        user_prompt: Prompt utilisateur.
        system_prompt: Prompt systeme versionne.

    Returns:
        Dict parse de la reponse LLM.

    Raises:
        requests.HTTPError: Si l'API retourne une erreur HTTP.
    """
    headers = {
        "x-api-key": api_key,
        "anthropic-version": _ANTHROPIC_VERSION_HEADER,
        "content-type": "application/json",
    }
    payload = {
        "model": model,
        "max_tokens": _DEFAULT_MAX_TOKENS,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_prompt}],
    }
    logger.info("Appel Anthropic API — modele : %s", model)
    response = requests.post(_ANTHROPIC_API_URL, headers=headers, json=payload, timeout=_TIMEOUT_SECONDS)
    response.raise_for_status()
    data = response.json()
    raw_text = data["content"][0]["text"]
    return _parse_json_response(raw_text)


def _call_openai(api_key: str, model: str, user_prompt: str, system_prompt: str) -> dict:
    """Appelle l'API OpenAI Chat Completions et parse la reponse JSON.

    Args:
        api_key: Cle API OpenAI (jamais loggee).
        model: Nom du modele.
        user_prompt: Prompt utilisateur.
        system_prompt: Prompt systeme.

    Returns:
        Dict parse de la reponse LLM.

    Raises:
        requests.HTTPError: Si l'API retourne une erreur HTTP.
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": _DEFAULT_MAX_TOKENS,
    }
    logger.info("Appel OpenAI API — modele : %s", model)
    response = requests.post(_OPENAI_API_URL, headers=headers, json=payload, timeout=_TIMEOUT_SECONDS)
    response.raise_for_status()
    data = response.json()
    raw_text = data["choices"][0]["message"]["content"]
    return _parse_json_response(raw_text)


def _call_ollama(model: str, user_prompt: str, system_prompt: str) -> dict:
    """Appelle Ollama local et parse la reponse JSON.

    Args:
        model: Nom du modele Ollama (ex: 'qwen2.5:14b').
        user_prompt: Prompt utilisateur.
        system_prompt: Prompt systeme.

    Returns:
        Dict parse de la reponse LLM.

    Raises:
        requests.HTTPError: Si Ollama retourne une erreur HTTP.
    """
    url = f"{OLLAMA_BASE_URL.rstrip('/')}/api/chat"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "format": "json",
    }
    logger.info("Appel Ollama local — modele : %s", model)
    response = requests.post(url, json=payload, timeout=_TIMEOUT_SECONDS)
    response.raise_for_status()
    data = response.json()
    raw_text = data["message"]["content"]
    return _parse_json_response(raw_text)


# ---------------------------------------------------------------------------
# Interface publique
# ---------------------------------------------------------------------------

def generate_recommendations(
    context: dict,
    provider: str = DEFAULT_AGENT_PROVIDER,
    model: str | None = None,
    api_key: str | None = None,
) -> dict:
    """Appelle le LLM selectionne et retourne les recommandations parsees.

    Mesure le temps de generation. Enrichit le resultat avec les metadonnees
    du provider et du modele utilises. La cle API n'est jamais loggee.

    Args:
        context: Dict retourne par build_recommendation_context().
        provider: 'anthropic' | 'openai' | 'ollama_local'.
        model: Nom du modele. None = utiliser le defaut du provider.
        api_key: Cle API. None = lire depuis config/env.

    Returns:
        Dict avec cles : analysis_summary, recommendations (list),
        watchlist_priorities, confidence_score, data_quality_note,
        provider_used, model_used, generation_ms, parse_success.

    Raises:
        ValueError: Si le provider n'est pas supporte.
    """
    system_prompt = get_system_prompt()
    user_prompt = _build_user_prompt(context)

    t_start = time.monotonic()

    if provider == "anthropic":
        resolved_model = model or "claude-sonnet-4-6"
        resolved_key = api_key or ANTHROPIC_API_KEY
        result = _call_anthropic(resolved_key, resolved_model, user_prompt, system_prompt)
    elif provider == "openai":
        resolved_model = model or "gpt-4o"
        resolved_key = api_key or OPENAI_API_KEY
        result = _call_openai(resolved_key, resolved_model, user_prompt, system_prompt)
    elif provider == "ollama_local":
        resolved_model = model or DEFAULT_AGENT_MODEL
        result = _call_ollama(resolved_model, user_prompt, system_prompt)
    else:
        raise ValueError(
            f"Provider non supporte : {provider!r}. "
            "Valeurs valides : anthropic, openai, ollama_local"
        )

    generation_ms = int((time.monotonic() - t_start) * 1000)

    result["provider_used"] = provider
    result["model_used"] = resolved_model
    result["generation_ms"] = generation_ms
    result.setdefault("parse_success", True)
    result.setdefault("recommendations", [])
    result.setdefault("watchlist_priorities", [])
    result.setdefault("confidence_score", 0.0)
    result.setdefault("data_quality_note", "")
    result.setdefault("analysis_summary", "")

    logger.info(
        "Generation complete — provider=%s modele=%s duree=%dms parse_success=%s",
        provider, resolved_model, generation_ms, result["parse_success"],
    )
    return result
