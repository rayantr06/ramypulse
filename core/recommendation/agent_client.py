"""Client LLM multi-provider pour la generation de recommandations marketing.

Supporte : anthropic, openai, google_gemini, ollama_local.
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

# Clé Gemini chargée depuis config/env
try:
    from config import GOOGLE_API_KEY as _GOOGLE_API_KEY
except ImportError:
    import os as _os
    _GOOGLE_API_KEY = _os.getenv("GOOGLE_API_KEY", "")

_ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
_OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
_GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models"
_ANTHROPIC_VERSION_HEADER = "2023-06-01"
_DEFAULT_MAX_TOKENS = 4096
_GEMINI_MAX_OUTPUT_TOKENS = 8192
_TIMEOUT_SECONDS = 180
_GEMINI_MAX_RECOMMENDATIONS = 2
_GEMINI_MAX_LIST_ITEMS = 2
_GEMINI_MAX_TEXT_CHARS = 240

# Catalogue des modèles recommandés par provider — utilisé par l'UI
MODEL_CATALOG: dict[str, list[dict]] = {
    "anthropic": [
        {"id": "claude-opus-4-6", "label": "Claude Opus 4.6 (le plus puissant)", "recommended": True},
        {"id": "claude-sonnet-4-6", "label": "Claude Sonnet 4.6 (équilibre coût/qualité)", "recommended": False},
        {"id": "claude-haiku-4-5-20251001", "label": "Claude Haiku 4.5 (rapide, économique)", "recommended": False},
    ],
    "openai": [
        {"id": "gpt-4o", "label": "GPT-4o (recommandé)", "recommended": True},
        {"id": "gpt-4-turbo", "label": "GPT-4 Turbo", "recommended": False},
        {"id": "o1-preview", "label": "o1 Preview (raisonnement avancé)", "recommended": False},
    ],
    "google_gemini": [
        {"id": "gemini-2.5-flash", "label": "Gemini 2.5 Flash (recommande)", "recommended": True},
        {"id": "gemini-2.5-pro", "label": "Gemini 2.5 Pro (plus puissant, quota dependant)", "recommended": False},
        {"id": "gemini-2.0-flash", "label": "Gemini 2.0 Flash (économique)", "recommended": False},
    ],
    "ollama_local": [
        {"id": "qwen2.5:14b", "label": "Qwen 2.5 14B (recommandé local)", "recommended": True},
        {"id": "llama3.2:3b", "label": "Llama 3.2 3B (léger)", "recommended": False},
        {"id": "mistral:7b", "label": "Mistral 7B", "recommended": False},
    ],
}

# Modèles par défaut par provider
_DEFAULT_MODELS: dict[str, str] = {
    "anthropic": "claude-opus-4-6",
    "openai": "gpt-4o",
    "google_gemini": "gemini-2.5-flash",
    "ollama_local": "qwen2.5:14b",
}


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

    # Tentative 4 : recuperer ce qui a deja ete genere avant une coupure MAX_TOKENS
    partial_payload = _recover_partial_json_payload(cleaned)
    if partial_payload is not None:
        return partial_payload

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


def _decode_json_string_token(token: str) -> str:
    """Decode une chaine JSON extraite via regex."""
    try:
        return json.loads(f'"{token}"')
    except json.JSONDecodeError:
        return token


def _extract_complete_json_objects(array_payload: str) -> list[dict]:
    """Extrait les objets JSON complets d'un tableau potentiellement tronque."""
    objects: list[dict] = []
    depth = 0
    start: int | None = None
    in_string = False
    escaped = False

    for index, char in enumerate(array_payload):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
            continue
        if char == "{":
            if depth == 0:
                start = index
            depth += 1
            continue
        if char == "}":
            if depth == 0:
                continue
            depth -= 1
            if depth == 0 and start is not None:
                fragment = array_payload[start : index + 1]
                try:
                    parsed = json.loads(fragment)
                except json.JSONDecodeError:
                    parsed = None
                if isinstance(parsed, dict):
                    objects.append(parsed)
                start = None
            continue
        if char == "]" and depth == 0:
            break

    return objects


def _recover_partial_json_payload(raw_text: str) -> dict | None:
    """Recupere un payload minimal quand le JSON est coupe en milieu de flux."""
    analysis_match = re.search(
        r'"analysis_summary"\s*:\s*"((?:\\.|[^"\\])*)"',
        raw_text,
        flags=re.DOTALL,
    )
    recommendations_match = re.search(
        r'"recommendations"\s*:\s*(\[[\s\S]*)',
        raw_text,
        flags=re.DOTALL,
    )
    confidence_match = re.search(r'"confidence_score"\s*:\s*([0-9]+(?:\.[0-9]+)?)', raw_text)
    watchlist_match = re.search(
        r'"watchlist_priorities"\s*:\s*(\[[\s\S]*?\])',
        raw_text,
        flags=re.DOTALL,
    )
    data_quality_match = re.search(
        r'"data_quality_note"\s*:\s*"((?:\\.|[^"\\])*)"',
        raw_text,
        flags=re.DOTALL,
    )

    analysis_summary = _decode_json_string_token(analysis_match.group(1)) if analysis_match else ""
    recommendations = (
        _extract_complete_json_objects(recommendations_match.group(1))
        if recommendations_match
        else []
    )

    if not analysis_summary and not recommendations:
        return None

    watchlist_priorities: list[str] = []
    if watchlist_match:
        try:
            parsed_watchlists = json.loads(watchlist_match.group(1))
        except json.JSONDecodeError:
            parsed_watchlists = []
        if isinstance(parsed_watchlists, list):
            watchlist_priorities = [str(item) for item in parsed_watchlists if str(item).strip()]

    confidence_score = 0.0
    if confidence_match:
        try:
            confidence_score = float(confidence_match.group(1))
        except ValueError:
            confidence_score = 0.0

    logger.warning(
        "Reponse LLM tronquee detectee. Recuperation partielle: %d recommendation(s) exploitable(s).",
        len(recommendations),
    )
    return {
        "analysis_summary": analysis_summary or "Reponse partielle du modele.",
        "recommendations": recommendations,
        "watchlist_priorities": watchlist_priorities,
        "confidence_score": confidence_score,
        "data_quality_note": (
            _decode_json_string_token(data_quality_match.group(1))
            if data_quality_match
            else "Reponse partielle du modele: sortie tronquee."
        ),
        "parse_success": False,
    }


# ---------------------------------------------------------------------------
# Construction du prompt utilisateur
# ---------------------------------------------------------------------------

def _compact_text(value: object, max_chars: int = _GEMINI_MAX_TEXT_CHARS) -> str:
    """Tronque defensivement un texte sans perdre l'information utile."""
    text = str(value or "").strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"


def _compact_gemini_context(context: dict) -> dict:
    """Construit un contexte plus compact pour Gemini afin d'eviter les reponses tronquees."""
    metrics = context.get("current_metrics", {})
    active_alerts = []
    for alert in context.get("active_alerts", [])[:3]:
        payload = alert.get("alert_payload") or {}
        active_alerts.append(
            {
                "alert_id": alert.get("alert_id"),
                "title": _compact_text(alert.get("title") or alert.get("alert_type") or "Alerte"),
                "severity": alert.get("severity"),
                "status": alert.get("status"),
                "watchlist_id": alert.get("watchlist_id"),
                "summary": _compact_text(
                    alert.get("message")
                    or payload.get("summary")
                    or payload.get("reason")
                    or payload.get("description")
                ),
                "source_urls": [
                    str(url)
                    for url in (payload.get("source_urls") or payload.get("post_urls") or [])[:_GEMINI_MAX_LIST_ITEMS]
                ],
            }
        )

    active_watchlists = []
    for watchlist in context.get("active_watchlists", [])[:3]:
        latest_metrics = watchlist.get("latest_metrics") or {}
        active_watchlists.append(
            {
                "watchlist_id": watchlist.get("watchlist_id"),
                "watchlist_name": watchlist.get("watchlist_name"),
                "channels": (watchlist.get("filters") or {}).get("channels", [])[:_GEMINI_MAX_LIST_ITEMS],
                "keywords": (watchlist.get("filters") or {}).get("keywords", [])[:_GEMINI_MAX_LIST_ITEMS],
                "nss": latest_metrics.get("nss"),
                "delta_nss": latest_metrics.get("delta_nss"),
                "volume_total": latest_metrics.get("volume_total"),
            }
        )

    recent_campaigns = []
    for campaign in context.get("recent_campaigns", [])[:2]:
        recent_campaigns.append(
            {
                "campaign_id": campaign.get("campaign_id"),
                "campaign_name": campaign.get("campaign_name"),
                "status": campaign.get("status"),
                "latest_uplift_nss": campaign.get("latest_uplift_nss"),
                "latest_volume_lift_pct": campaign.get("latest_volume_lift_pct"),
            }
        )

    rag_chunks = []
    for chunk in context.get("rag_chunks", [])[:3]:
        rag_chunks.append(
            {
                "text": _compact_text(chunk.get("text"), max_chars=280),
                "channel": chunk.get("channel"),
                "timestamp": chunk.get("timestamp"),
            }
        )

    return {
        "client_profile": context.get("client_profile", {}),
        "trigger": context.get("trigger", {}),
        "current_metrics": {
            "nss_global": metrics.get("nss_global"),
            "nss_by_aspect": metrics.get("nss_by_aspect"),
            "nss_by_channel": metrics.get("nss_by_channel"),
            "volume_total": metrics.get("volume_total"),
            "top_negative_aspects": (metrics.get("top_negative_aspects") or [])[:_GEMINI_MAX_LIST_ITEMS],
        },
        "active_alerts": active_alerts,
        "active_watchlists": active_watchlists,
        "recent_campaigns": recent_campaigns,
        "rag_chunks": rag_chunks,
        "data_quality": context.get("data_quality", {}),
    }


def _build_user_prompt(context: dict, provider: str) -> str:
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

    if provider == "google_gemini":
        compact_context = _compact_gemini_context(context)
        return (
            "Voici un resume compact des donnees RamyPulse a analyser.\n\n"
            f"{json.dumps(compact_context, ensure_ascii=False, indent=2)}\n\n"
            "Contraintes obligatoires de sortie:\n"
            f"- retourne EXACTEMENT {_GEMINI_MAX_RECOMMENDATIONS} recommandations maximum\n"
            "- analysis_summary: 2 phrases maximum\n"
            "- rationale: 2 phrases maximum\n"
            f"- target_regions, hooks, key_messages, watchlist_priorities: {_GEMINI_MAX_LIST_ITEMS} elements maximum\n"
            "- garde les champs textuels concis mais complets\n"
            "- reponds UNIQUEMENT en JSON valide selon le schema demande\n"
        )

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


def _build_system_prompt(provider: str) -> str:
    """Ajoute des garde-fous provider-specifiques sans forcer un modele."""
    system_prompt = get_system_prompt()
    if provider != "google_gemini":
        return system_prompt
    return (
        system_prompt
        + "\n\nCONTRAINTE ADDITIONNELLE POUR GEMINI:\n"
        + f"- maximum {_GEMINI_MAX_RECOMMENDATIONS} recommandations\n"
        + "- chaque champ texte doit rester court et directement fonde sur les donnees\n"
        + f"- maximum {_GEMINI_MAX_LIST_ITEMS} hooks, key_messages, target_regions et watchlist_priorities\n"
        + "- priorise des sorties completes plutot que nombreuses\n"
    )


def _default_data_basis(context: dict) -> str:
    """Construit une base de donnees minimale quand le LLM oublie de la fournir."""
    metrics = context.get("current_metrics", {})
    volume_total = metrics.get("volume_total", 0)
    nss_global = metrics.get("nss_global")
    top_negative = metrics.get("top_negative_aspects", [])
    top_negative_text = ", ".join(top_negative[:2]) if top_negative else "aucun aspect prioritaire"
    nss_text = "indisponible" if nss_global is None else f"{float(nss_global):.1f}"
    return (
        f"Base RamyPulse: NSS global {nss_text}, volume {int(volume_total)} signaux, "
        f"aspects prioritaires {top_negative_text}."
    )


def _default_data_quality_note(context: dict) -> str:
    """Construit une note de qualite si le modele n'en donne pas."""
    quality = context.get("data_quality", {})
    volume_total = int(quality.get("volume_total") or context.get("current_metrics", {}).get("volume_total", 0) or 0)
    channel_count = int(quality.get("channel_count") or 0)
    rag_chunk_count = int(quality.get("rag_chunk_count") or len(context.get("rag_chunks", [])))
    notes: list[str] = [f"{volume_total} signaux"]
    if channel_count:
        notes.append(f"{channel_count} canal(aux)")
    notes.append(f"{rag_chunk_count} extrait(s) RAG")
    if volume_total < 50:
        notes.append("fiabilite limitee: volume faible")
    if channel_count <= 1:
        notes.append("couverture limitee: dataset mono-canal")
    return ". ".join(notes) + "."


def _normalize_recommendation_item(item: dict, context: dict, index: int) -> dict:
    """Complete une recommandation partielle avec des champs defensifs."""
    normalized = dict(item or {})
    normalized.setdefault("id", f"rec_{index:03d}")
    normalized.setdefault("priority", "medium")
    normalized.setdefault("type", "content_organic")
    normalized.setdefault("title", f"Recommendation {index}")
    normalized.setdefault("rationale", "A confirmer a partir des donnees RamyPulse.")
    normalized.setdefault("target_platform", "multi_platform")
    normalized.setdefault("target_segment", "audience Ramy prioritaire")
    normalized.setdefault("target_regions", [])
    normalized.setdefault("target_aspects", context.get("current_metrics", {}).get("top_negative_aspects", [])[:2])
    normalized.setdefault("timing", {"urgency": "within_week", "best_moment": "des que possible"})
    normalized.setdefault(
        "influencer_profile",
        {"tier": "none", "niche": "", "tone": "", "engagement_focus": ""},
    )
    content = dict(normalized.get("content") or {})
    hooks = [str(hook).strip() for hook in content.get("hooks", []) if str(hook).strip()]
    if not hooks:
        title = normalized.get("title", "Action Ramy")
        hooks = [
            f"{title} - version francaise claire",
            f"{title} - formule darija simple pour reseaux sociaux",
        ]
    content["hooks"] = hooks
    content.setdefault("script_outline", "")
    content.setdefault("key_messages", [])
    content.setdefault("visual_direction", "")
    content.setdefault("call_to_action", "")
    normalized["content"] = content
    normalized["data_basis"] = str(normalized.get("data_basis") or "").strip() or _default_data_basis(context)
    return normalized


def _finalize_result_payload(result: dict, context: dict) -> dict:
    """Normalise la reponse LLM et applique les garde-fous qualite produit."""
    payload = dict(result)
    recommendations = payload.get("recommendations", [])
    if not isinstance(recommendations, list):
        recommendations = []
    payload["recommendations"] = [
        _normalize_recommendation_item(item if isinstance(item, dict) else {}, context, index)
        for index, item in enumerate(recommendations, start=1)
    ]

    try:
        confidence = float(payload.get("confidence_score", 0.0) or 0.0)
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = max(0.0, min(1.0, confidence))
    volume_total = int(context.get("current_metrics", {}).get("volume_total", 0) or 0)
    if volume_total < 50:
        confidence = min(confidence, 0.45)
    payload["confidence_score"] = round(confidence, 2)
    payload["data_quality_note"] = str(payload.get("data_quality_note") or "").strip() or _default_data_quality_note(context)
    payload["analysis_summary"] = str(payload.get("analysis_summary") or "").strip()
    return payload


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


def _call_gemini(api_key: str, model: str, user_prompt: str, system_prompt: str) -> dict:
    """Appelle l'API Google Gemini et parse la reponse JSON.

    Args:
        api_key: Cle API Google (jamais loggee).
        model: Nom du modele Gemini.
        user_prompt: Prompt utilisateur.
        system_prompt: Prompt systeme.

    Returns:
        Dict parse de la reponse LLM.

    Raises:
        requests.HTTPError: Si l'API retourne une erreur HTTP.
    """
    url = f"{_GEMINI_API_URL}/{model}:generateContent"
    headers = {"Content-Type": "application/json"}
    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"parts": [{"text": user_prompt}]}],
        "generationConfig": {
            "maxOutputTokens": _GEMINI_MAX_OUTPUT_TOKENS,
            "responseMimeType": "application/json",
        },
    }
    logger.info("Appel Gemini API — modele : %s", model)
    response = requests.post(
        url, headers=headers, json=payload,
        params={"key": api_key},
        timeout=_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    data = response.json()
    raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
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
    provider: str | None = None,
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
    resolved_provider = str(provider or DEFAULT_AGENT_PROVIDER or "google_gemini").strip() or "google_gemini"
    system_prompt = _build_system_prompt(resolved_provider)
    user_prompt = _build_user_prompt(context, resolved_provider)

    t_start = time.monotonic()

    if resolved_provider == "anthropic":
        resolved_model = model or _DEFAULT_MODELS["anthropic"]
        resolved_key = api_key or ANTHROPIC_API_KEY
        result = _call_anthropic(resolved_key, resolved_model, user_prompt, system_prompt)
    elif resolved_provider == "openai":
        resolved_model = model or _DEFAULT_MODELS["openai"]
        resolved_key = api_key or OPENAI_API_KEY
        result = _call_openai(resolved_key, resolved_model, user_prompt, system_prompt)
    elif resolved_provider == "google_gemini":
        resolved_model = model or _DEFAULT_MODELS["google_gemini"]
        resolved_key = api_key or _GOOGLE_API_KEY
        result = _call_gemini(resolved_key, resolved_model, user_prompt, system_prompt)
    elif resolved_provider == "ollama_local":
        resolved_model = model or _DEFAULT_MODELS.get("ollama_local", DEFAULT_AGENT_MODEL)
        result = _call_ollama(resolved_model, user_prompt, system_prompt)
    else:
        raise ValueError(
            f"Provider non supporte : {resolved_provider!r}. "
            "Valeurs valides : anthropic, openai, google_gemini, ollama_local"
        )

    generation_ms = int((time.monotonic() - t_start) * 1000)

    result = _finalize_result_payload(result, context)
    result["provider_used"] = resolved_provider
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
        resolved_provider, resolved_model, generation_ms, result["parse_success"],
    )
    return result
