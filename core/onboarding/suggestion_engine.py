"""Suggestion engine for smart onboarding."""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Iterable
from typing import Any
from urllib.parse import urlparse

import requests

import config


logger = logging.getLogger(__name__)

_OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
_OPENAI_MODEL = "gpt-4o-mini"
_VALID_SOURCE_CHANNELS = {"facebook", "instagram", "google_maps", "youtube", "public_url_seed"}
_VALID_RECOMMENDED_CHANNELS = {
    "public_url_seed",
    "web_search",
    "facebook",
    "instagram",
    "google_maps",
    "youtube",
}
_VALID_SCOPE_TYPES = {"watch_seed", "product", "region", "channel", "cross_dimension"}
_PREFERRED_CHANNEL_ORDER = [
    "facebook",
    "instagram",
    "google_maps",
    "youtube",
    "web_search",
    "public_url_seed",
]
_CITY_HINTS = {
    "alger": "alger",
    "oran": "oran",
    "constantine": "constantine",
    "setif": "setif",
    "blida": "blida",
    "bejaia": "bejaia",
    "annaba": "annaba",
}

_SYSTEM_PROMPT = """
Tu es un assistant de veille marketing pour des marques algeriennes.
Transforme les signaux publics fournis en un JSON strict avec ces cles snake_case:
- tenant_setup
- suggested_sources
- required_credentials
- recommended_channels
- suggested_watchlists
- suggested_alert_profiles
- deferred_agent_config
- warnings

Contraintes obligatoires:
- ne cree jamais de source admin web
- les URLs web publiques restent des suggested_sources channel=public_url_seed
- les watchlists doivent contenir exactement 1 scope_type=watch_seed et 2 a 4 watchlists d'analyse
- scope_type autorises: watch_seed, product, region, channel, cross_dimension
- ne retourne jamais scope_type=manual
- les alert profiles restent separes des watchlists
- ne propose ni campagnes ni recommandations operationnelles deja generees

Reponds uniquement en JSON valide.
""".strip()


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
    return slug.strip("-") or "brand-dz"


def _coerce_string(value: object, fallback: str = "") -> str:
    return str(value).strip() if value is not None else fallback


def _coerce_bool(value: object, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "oui"}:
            return True
        if lowered in {"0", "false", "no", "non"}:
            return False
    return default


def _coerce_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_url(value: object) -> str | None:
    text = _coerce_string(value)
    if not text:
        return None
    if text.startswith("//"):
        text = f"https:{text}"
    if not re.match(r"^https?://", text, flags=re.IGNORECASE):
        return None
    return text


def _unique_strings(values: Iterable[object], *, lowercase: bool = False) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = _coerce_string(value)
        if not text:
            continue
        candidate = text.lower() if lowercase else text
        if candidate in seen:
            continue
        seen.add(candidate)
        normalized.append(candidate)
    return normalized


def _safe_dict_list(value: object) -> list[dict[str, Any]]:
    return [item for item in (value or []) if isinstance(item, dict)]


def _parse_json_response(raw_text: str) -> dict[str, Any]:
    for candidate in (raw_text, re.sub(r"```json\s*|\s*```", "", raw_text, flags=re.DOTALL).strip()):
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed

    match = re.search(r"\{.*\}", raw_text, flags=re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group())
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _source_from_url(url: str) -> tuple[str, str]:
    host = urlparse(url).netloc.lower()
    if "facebook.com" in host or host.endswith("fb.com"):
        return "facebook", "facebook_page"
    if "instagram.com" in host:
        return "instagram", "instagram_profile"
    if "youtube.com" in host or "youtu.be" in host:
        return "youtube", "youtube_channel"
    if "google." in host and "maps" in url.lower():
        return "google_maps", "google_maps_place"
    return "public_url_seed", "website"


def _google_maps_url(item: dict[str, Any]) -> str | None:
    website = _normalize_url(item.get("website"))
    if website:
        return website
    place_id = _coerce_string(item.get("place_id"))
    if place_id:
        return f"https://www.google.com/maps/place/?q=place_id:{place_id}"
    return None


def _extract_sources_from_serp(serp_signals: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    seen_urls: set[str] = set()

    for item in _safe_dict_list(serp_signals.get("organic")):
        url = _normalize_url(item.get("link"))
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        channel, source_type = _source_from_url(url)
        candidates.append(
            {
                "type": source_type,
                "label": _coerce_string(item.get("title"), url),
                "url": url,
                "channel": channel,
                "confidence": 0.9 if channel != "public_url_seed" else 0.82,
                "status": "requires_credentials" if channel in {"facebook", "instagram"} else "suggested_only",
                "reason": _coerce_string(item.get("snippet"), "Signal detecte via recherche publique."),
            }
        )

    for item in _safe_dict_list(serp_signals.get("local")):
        url = _google_maps_url(item)
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        candidates.append(
            {
                "type": "google_maps_place",
                "label": _coerce_string(item.get("title"), "Point de vente detecte"),
                "url": url,
                "channel": "google_maps",
                "confidence": 0.78,
                "status": "suggested_only",
                "reason": _coerce_string(item.get("address"), "Presence locale detectee."),
            }
        )

    return candidates[:6]


def _preferred_channel(channels: Iterable[str]) -> str | None:
    values = list(channels)
    for channel in _PREFERRED_CHANNEL_ORDER:
        if channel in values:
            return channel
    return None


def _guess_region(serp_signals: dict[str, Any]) -> str | None:
    for item in _safe_dict_list(serp_signals.get("local")):
        haystack = " ".join(
            [
                _coerce_string(item.get("title")).lower(),
                _coerce_string(item.get("address")).lower(),
            ]
        )
        for city, normalized in _CITY_HINTS.items():
            if city in haystack:
                return normalized
    return None


def _default_tenant_setup(raw: dict[str, Any], brand_name: str) -> dict[str, Any]:
    client_name = _coerce_string(raw.get("client_name")) or brand_name.strip()
    client_slug = _slugify(_coerce_string(raw.get("client_slug")) or client_name)
    country = _coerce_string(raw.get("country"), "DZ").upper() or "DZ"
    return {
        "client_name": client_name,
        "client_slug": client_slug,
        "country": country,
    }


def _normalize_source(raw: dict[str, Any]) -> dict[str, Any] | None:
    url = _normalize_url(raw.get("url"))
    if not url:
        return None
    derived_channel, derived_type = _source_from_url(url)
    channel = _coerce_string(raw.get("channel")) or derived_channel
    if channel not in _VALID_SOURCE_CHANNELS:
        channel = derived_channel
    if channel not in _VALID_SOURCE_CHANNELS:
        return None

    source_type = _coerce_string(raw.get("type")) or derived_type
    if channel == "public_url_seed":
        source_type = "website"
    elif channel == "facebook":
        source_type = "facebook_page"
    elif channel == "instagram":
        source_type = "instagram_profile"
    elif channel == "youtube":
        source_type = "youtube_channel"
    elif channel == "google_maps":
        source_type = "google_maps_place"

    confidence = max(0.0, min(1.0, _coerce_float(raw.get("confidence"), 0.7)))
    status = _coerce_string(raw.get("status")) or (
        "requires_credentials" if channel in {"facebook", "instagram"} else "suggested_only"
    )
    reason = _coerce_string(raw.get("reason")) or "Suggestion issue de l'analyse publique."
    label = _coerce_string(raw.get("label")) or urlparse(url).netloc or url
    return {
        "type": source_type,
        "label": label,
        "url": url,
        "channel": channel,
        "confidence": round(confidence, 2),
        "status": status,
        "reason": reason,
    }


def _normalize_sources(raw_sources: object, serp_signals: dict[str, Any]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    seen_urls: set[str] = set()

    for source in _safe_dict_list(raw_sources):
        candidate = _normalize_source(source)
        if candidate is None or candidate["url"] in seen_urls:
            continue
        seen_urls.add(candidate["url"])
        normalized.append(candidate)

    for source in _extract_sources_from_serp(serp_signals):
        if source["url"] in seen_urls:
            continue
        seen_urls.add(source["url"])
        normalized.append(source)

    return normalized[:6]


def _build_recommended_channels(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    channels: list[dict[str, Any]] = [
        {
            "channel": "web_search",
            "enabled_by_default": True,
            "reason": "Canal de decouverte public pour le premier run.",
        }
    ]
    seen = {"web_search"}

    if any(source["channel"] == "public_url_seed" for source in sources):
        channels.append(
            {
                "channel": "public_url_seed",
                "enabled_by_default": True,
                "reason": "URLs publiques detectees pour alimenter watch_seed.",
            }
        )
        seen.add("public_url_seed")

    for source in sources:
        channel = source["channel"]
        if channel in seen or channel not in _VALID_RECOMMENDED_CHANNELS:
            continue
        channels.append(
            {
                "channel": channel,
                "enabled_by_default": True,
                "reason": source["reason"],
            }
        )
        seen.add(channel)

    return channels


def _build_required_credentials(
    raw_credentials: object,
    sources: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for credential in _safe_dict_list(raw_credentials):
        platform = _coerce_string(credential.get("platform")).lower()
        credential_type = _coerce_string(credential.get("credential_type"))
        if not platform or not credential_type:
            continue
        key = (platform, credential_type)
        if key in seen:
            continue
        seen.add(key)
        normalized.append(
            {
                "platform": platform,
                "credential_type": credential_type,
                "required": _coerce_bool(credential.get("required"), True),
                "reason": _coerce_string(credential.get("reason"))
                or "Credential requis pour activer la source proposee.",
            }
        )

    existing_platforms = {item["platform"] for item in normalized}
    inferred = {
        "facebook": ("oauth_access_token", "Page Facebook admin detectee."),
        "instagram": ("oauth_access_token", "Profil Instagram admin detecte."),
        "youtube": ("api_key", "Canal YouTube detecte."),
        "google_maps": ("api_key", "Point Google Maps detecte."),
    }
    for source in sources:
        platform = source["channel"]
        if platform not in inferred or platform in existing_platforms:
            continue
        credential_type, reason = inferred[platform]
        normalized.append(
            {
                "platform": platform,
                "credential_type": credential_type,
                "required": True,
                "reason": reason,
            }
        )
        existing_platforms.add(platform)

    return normalized


def _default_watch_seed_filters(
    brand_name: str,
    product_name: str | None,
    seed_urls: list[str],
    channels: list[str],
) -> dict[str, Any]:
    keywords = _unique_strings(
        [
            brand_name,
            *brand_name.split(),
            product_name or "",
        ],
        lowercase=True,
    )
    return {
        "brand_name": brand_name,
        "product_name": product_name.strip() if isinstance(product_name, str) and product_name.strip() else None,
        "keywords": keywords,
        "seed_urls": seed_urls,
        "competitors": [],
        "channels": channels,
        "languages": ["fr", "ar"],
        "hashtags": [],
        "period_days": 7,
        "min_volume": 10,
    }


def _normalize_analysis_filters(
    scope_type: str,
    raw_filters: object,
    *,
    preferred_channel: str | None,
    product_name: str | None,
    region_name: str | None,
) -> dict[str, Any]:
    raw = raw_filters if isinstance(raw_filters, dict) else {}
    filters = {
        "channel": _coerce_string(raw.get("channel")) or None,
        "aspect": _coerce_string(raw.get("aspect")) or None,
        "wilaya": _coerce_string(raw.get("wilaya")).lower() or None,
        "product": _coerce_string(raw.get("product")) or None,
        "sentiment": _coerce_string(raw.get("sentiment")) or None,
        "period_days": max(1, int(_coerce_float(raw.get("period_days"), 7))),
        "min_volume": max(0, int(_coerce_float(raw.get("min_volume"), 10))),
    }

    if scope_type == "product" and not filters["product"]:
        filters["product"] = _coerce_string(product_name) or None
    if scope_type == "channel" and not filters["channel"]:
        filters["channel"] = preferred_channel
    if scope_type == "region" and not filters["wilaya"]:
        filters["wilaya"] = region_name or "alger"
    if scope_type == "cross_dimension":
        if not filters["channel"]:
            filters["channel"] = preferred_channel
        if not filters["aspect"]:
            filters["aspect"] = "disponibilite"

    return filters


def _build_default_analysis_watchlists(
    brand_name: str,
    product_name: str | None,
    *,
    preferred_channel: str | None,
    region_name: str | None,
) -> list[dict[str, Any]]:
    safe_product = _coerce_string(product_name) or brand_name
    watchlists = [
        {
            "name": f"{brand_name} produit",
            "description": f"Analyse produit concentree sur {safe_product}.",
            "scope_type": "product",
            "role": "analysis",
            "filters": _normalize_analysis_filters(
                "product",
                {"product": safe_product},
                preferred_channel=preferred_channel,
                product_name=product_name,
                region_name=region_name,
            ),
            "enabled_by_default": True,
            "reason": "Suivre les signaux produits du premier perimetre.",
        },
        {
            "name": f"{brand_name} canal",
            "description": "Analyse des signaux sur le canal principal detecte.",
            "scope_type": "channel",
            "role": "analysis",
            "filters": _normalize_analysis_filters(
                "channel",
                {"channel": preferred_channel},
                preferred_channel=preferred_channel,
                product_name=product_name,
                region_name=region_name,
            ),
            "enabled_by_default": True,
            "reason": "Conserver un axe canal pour alertes et lecture rapide.",
        },
        {
            "name": f"{brand_name} tension",
            "description": "Croise canal et aspect negatif a surveiller.",
            "scope_type": "cross_dimension",
            "role": "analysis",
            "filters": _normalize_analysis_filters(
                "cross_dimension",
                {"channel": preferred_channel, "aspect": "disponibilite"},
                preferred_channel=preferred_channel,
                product_name=product_name,
                region_name=region_name,
            ),
            "enabled_by_default": True,
            "reason": "Preparer un axe prioritaire pour les futures alertes.",
        },
    ]
    if region_name:
        watchlists.append(
            {
                "name": f"{brand_name} {region_name}",
                "description": f"Analyse locale sur {region_name.title()}.",
                "scope_type": "region",
                "role": "analysis",
                "filters": _normalize_analysis_filters(
                    "region",
                    {"wilaya": region_name},
                    preferred_channel=preferred_channel,
                    product_name=product_name,
                    region_name=region_name,
                ),
                "enabled_by_default": True,
                "reason": "Un signal local a ete detecte dans les resultats publics.",
            }
        )
    return watchlists


def _build_watchlists(
    raw_watchlists: object,
    *,
    brand_name: str,
    product_name: str | None,
    sources: list[dict[str, Any]],
    recommended_channels: list[dict[str, Any]],
    serp_signals: dict[str, Any],
) -> list[dict[str, Any]]:
    enabled_channels = [
        item["channel"]
        for item in recommended_channels
        if item["enabled_by_default"] and item["channel"] in _VALID_RECOMMENDED_CHANNELS
    ]
    seed_urls = [source["url"] for source in sources if source["channel"] == "public_url_seed"]
    preferred_channel = _preferred_channel(enabled_channels)
    region_name = _guess_region(serp_signals)

    watch_seed = {
        "name": f"{brand_name} watch seed",
        "description": "Collecte de depart et perimetre de decouverte.",
        "scope_type": "watch_seed",
        "role": "seed",
        "filters": _default_watch_seed_filters(brand_name, product_name, seed_urls, enabled_channels),
        "enabled_by_default": True,
        "reason": "Watchlist racine obligatoire pour le premier run.",
    }

    normalized_analysis: list[dict[str, Any]] = []
    seen_names: set[str] = set()
    for watchlist in _safe_dict_list(raw_watchlists):
        scope_type = _coerce_string(watchlist.get("scope_type"))
        if scope_type not in _VALID_SCOPE_TYPES or scope_type == "watch_seed":
            continue
        name = _coerce_string(watchlist.get("name")) or f"{brand_name} {scope_type}"
        if name in seen_names:
            continue
        seen_names.add(name)
        normalized_analysis.append(
            {
                "name": name,
                "description": _coerce_string(watchlist.get("description")),
                "scope_type": scope_type,
                "role": "analysis",
                "filters": _normalize_analysis_filters(
                    scope_type,
                    watchlist.get("filters"),
                    preferred_channel=preferred_channel,
                    product_name=product_name,
                    region_name=region_name,
                ),
                "enabled_by_default": _coerce_bool(watchlist.get("enabled_by_default"), True),
                "reason": _coerce_string(watchlist.get("reason")) or "Watchlist d'analyse proposee.",
            }
        )

    for fallback_watchlist in _build_default_analysis_watchlists(
        brand_name,
        product_name,
        preferred_channel=preferred_channel,
        region_name=region_name,
    ):
        if len(normalized_analysis) >= 4:
            break
        if fallback_watchlist["name"] in seen_names:
            continue
        seen_names.add(fallback_watchlist["name"])
        normalized_analysis.append(fallback_watchlist)

    return [watch_seed, *normalized_analysis[:4]]


def _watchlist_ref(name: str) -> str:
    return _slugify(name)


def _build_alert_profiles(
    raw_profiles: object,
    watchlists: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    analysis_watchlists = [watchlist for watchlist in watchlists if watchlist["role"] == "analysis"]
    normalized: list[dict[str, Any]] = []

    for profile in _safe_dict_list(raw_profiles):
        watchlist_ref = _coerce_string(profile.get("watchlist_ref"))
        profile_name = _coerce_string(profile.get("profile_name"))
        if not watchlist_ref or not profile_name:
            continue
        rules = []
        for rule in _safe_dict_list(profile.get("rules")):
            rule_id = _coerce_string(rule.get("rule_id"))
            if not rule_id:
                continue
            rules.append(
                {
                    "rule_id": rule_id,
                    "threshold_value": rule.get("threshold_value"),
                    "comparator": _coerce_string(rule.get("comparator"), "gt"),
                    "lookback_window": _coerce_string(rule.get("lookback_window"), "7d"),
                    "severity_level": _coerce_string(rule.get("severity_level"), "high"),
                    "reason": _coerce_string(rule.get("reason")),
                }
            )
        if not rules:
            continue
        normalized.append(
            {
                "watchlist_ref": watchlist_ref,
                "profile_name": profile_name,
                "enabled_by_default": _coerce_bool(profile.get("enabled_by_default"), True),
                "rules": rules,
                "reason": _coerce_string(profile.get("reason")) or "Profil d'alerte propose.",
            }
        )

    if normalized:
        return normalized

    profiles: list[dict[str, Any]] = []
    for watchlist in analysis_watchlists[:2]:
        profiles.append(
            {
                "watchlist_ref": _watchlist_ref(watchlist["name"]),
                "profile_name": f"Alerte {watchlist['name']}",
                "enabled_by_default": True,
                "rules": [
                    {
                        "rule_id": "negative_volume_surge",
                        "threshold_value": 60,
                        "comparator": "gt",
                        "lookback_window": "7d",
                        "severity_level": "high",
                        "reason": "Detecter les pics negatifs.",
                    },
                    {
                        "rule_id": "nss_critical_low",
                        "threshold_value": 20,
                        "comparator": "lt",
                        "lookback_window": "7d",
                        "severity_level": "high",
                        "reason": "Detecter un NSS faible.",
                    },
                ],
                "reason": "Bloc d'alertes propose pour la revue onboarding.",
            }
        )
    return profiles


def _build_deferred_agent_config(raw: object) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for item in _safe_dict_list(raw):
        key = _coerce_string(item.get("key"))
        if not key:
            continue
        normalized.append(
            {
                "key": key,
                "value": item.get("value"),
                "reason": _coerce_string(item.get("reason"))
                or "Configuration agent differee apres validation humaine.",
            }
        )
    if normalized:
        return normalized
    return [
        {
            "key": "weekly_digest",
            "value": True,
            "reason": "Conserver une suggestion agent sans l'appliquer automatiquement au V1.",
        }
    ]


def _build_warnings(
    raw_warnings: object,
    *,
    fallback_used: bool,
    sources: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    seen_codes: set[str] = set()

    def _append(code: str, message: str, severity: str) -> None:
        if code in seen_codes:
            return
        seen_codes.add(code)
        warnings.append({"code": code, "message": message, "severity": severity})

    for item in _safe_dict_list(raw_warnings):
        code = _coerce_string(item.get("code"))
        message = _coerce_string(item.get("message"))
        severity = _coerce_string(item.get("severity"), "warning") or "warning"
        if code and message:
            _append(code, message, severity)

    public_urls = [source for source in sources if source["channel"] == "public_url_seed"]
    if not public_urls:
        _append(
            "no_official_site",
            "Aucun site officiel clair n'a ete detecte. Verifiez manuellement les seed URLs.",
            "warning",
        )

    by_channel: dict[str, int] = {}
    for source in sources:
        by_channel[source["channel"]] = by_channel.get(source["channel"], 0) + 1
    if by_channel.get("facebook", 0) > 1 or by_channel.get("instagram", 0) > 1:
        _append(
            "multiple_social_pages",
            "Plusieurs pages sociales plausibles ont ete detectees. Une revue humaine est recommandee.",
            "warning",
        )

    if len(public_urls) > 1:
        _append(
            "ambiguous_brand",
            "Plusieurs URLs publiques plausibles ont ete detectees pour la marque.",
            "warning",
        )

    if fallback_used:
        _append(
            "provider_unavailable",
            "Analyse heuristique utilisee car SerpApi ou OpenAI est indisponible localement.",
            "warning",
        )

    return warnings


def normalize_onboarding_analysis(
    raw_analysis: dict[str, Any] | None,
    *,
    brand_name: str,
    product_name: str | None,
    serp_signals: dict[str, Any],
    fallback_used: bool,
) -> dict[str, Any]:
    """Normalize any raw analysis into the enforced product contract."""
    raw = raw_analysis if isinstance(raw_analysis, dict) else {}
    tenant_setup = _default_tenant_setup(
        raw.get("tenant_setup") if isinstance(raw.get("tenant_setup"), dict) else {},
        brand_name,
    )
    sources = _normalize_sources(raw.get("suggested_sources"), serp_signals)
    recommended_channels = _build_recommended_channels(sources)
    watchlists = _build_watchlists(
        raw.get("suggested_watchlists"),
        brand_name=tenant_setup["client_name"],
        product_name=product_name,
        sources=sources,
        recommended_channels=recommended_channels,
        serp_signals=serp_signals,
    )
    return {
        "tenant_setup": tenant_setup,
        "suggested_sources": sources,
        "required_credentials": _build_required_credentials(raw.get("required_credentials"), sources),
        "recommended_channels": recommended_channels,
        "suggested_watchlists": watchlists,
        "suggested_alert_profiles": _build_alert_profiles(raw.get("suggested_alert_profiles"), watchlists),
        "deferred_agent_config": _build_deferred_agent_config(raw.get("deferred_agent_config")),
        "warnings": _build_warnings(raw.get("warnings"), fallback_used=fallback_used, sources=sources),
        "fallback_used": fallback_used,
    }


def _call_openai(user_prompt: str) -> dict[str, Any]:
    response = requests.post(
        _OPENAI_API_URL,
        headers={
            "Authorization": f"Bearer {config.OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": _OPENAI_MODEL,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
        },
        timeout=60,
    )
    response.raise_for_status()
    raw_content = _coerce_string(response.json()["choices"][0]["message"]["content"])
    return _parse_json_response(raw_content)


def build_suggestions(
    *,
    brand_name: str,
    serp_signals: dict[str, Any],
    product_name: str | None = None,
) -> dict[str, Any]:
    """Build structured onboarding suggestions from discovery signals."""
    raw_analysis: dict[str, Any] | None = None
    fallback_used = serp_signals.get("skipped", False) or not config.OPENAI_API_KEY

    if not fallback_used:
        try:
            raw_analysis = _call_openai(
                json.dumps(
                    {
                        "brand_name": brand_name,
                        "product_name": product_name,
                        "country": "DZ",
                        "organic": serp_signals.get("organic", []),
                        "local": serp_signals.get("local", []),
                    },
                    ensure_ascii=False,
                )
            )
        except Exception as exc:  # pragma: no cover - provider/network failure
            logger.warning("OpenAI onboarding suggestion call failed: %s", exc)
            fallback_used = True

    return normalize_onboarding_analysis(
        raw_analysis,
        brand_name=brand_name.strip(),
        product_name=product_name,
        serp_signals=serp_signals,
        fallback_used=fallback_used,
    )
