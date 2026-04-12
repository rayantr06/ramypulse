"""Service layer for smart onboarding analyze -> review -> confirm."""

from __future__ import annotations

from typing import Any

from core.ingestion.orchestrator import IngestionOrchestrator
from core.onboarding.brand_discovery import discover_brand_signals
from core.onboarding.suggestion_engine import _slugify, build_suggestions
from core.tenancy.client_manager import get_or_create_client, set_active_client
from core.watch_runs.run_service import start_watch_run, validate_requested_channels
from core.watchlists.watchlist_manager import create_watchlist


_SUPPORTED_ADMIN_SOURCE_CHANNELS = {"facebook", "instagram", "google_maps", "youtube", "import"}


def analyze_brand(
    *,
    brand_name: str,
    product_name: str | None = None,
    country: str = "dz",
) -> dict[str, Any]:
    brand = brand_name.strip()
    if not brand:
        raise ValueError("brand_name is required")

    serp_signals = discover_brand_signals(
        brand_name=brand,
        product_name=product_name,
        country=country,
    )
    return build_suggestions(
        brand_name=brand,
        product_name=product_name,
        serp_signals=serp_signals,
    )


def _dedupe_channels(channels: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for item in channels:
        channel = str(item or "").strip()
        if not channel or channel in seen:
            continue
        seen.add(channel)
        normalized.append(channel)
    return normalized


def _split_watchlists(selected_watchlists: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    watch_seed = [watchlist for watchlist in selected_watchlists if watchlist.get("scope_type") == "watch_seed"]
    analysis_watchlists = [
        watchlist for watchlist in selected_watchlists if watchlist.get("scope_type") != "watch_seed"
    ]
    if len(watch_seed) != 1:
        raise ValueError("exactly one watch_seed watchlist must be selected")
    if not 2 <= len(analysis_watchlists) <= 4:
        raise ValueError("between 2 and 4 analysis watchlists must be selected")
    return watch_seed[0], analysis_watchlists


def _merge_watch_seed_filters(
    watch_seed: dict[str, Any],
    *,
    brand_name: str,
    selected_channels: list[str],
    selected_sources: list[dict[str, Any]],
) -> dict[str, Any]:
    filters = dict(watch_seed.get("filters") or {})
    seed_urls = list(filters.get("seed_urls") or [])
    for source in selected_sources:
        if source.get("channel") == "public_url_seed" and source.get("url"):
            url = str(source["url"]).strip()
            if url and url not in seed_urls:
                seed_urls.append(url)
    filters["brand_name"] = str(filters.get("brand_name") or brand_name).strip()
    filters["seed_urls"] = seed_urls
    filters["channels"] = selected_channels
    filters.setdefault("keywords", [keyword for keyword in _slugify(brand_name).split("-") if keyword])
    filters.setdefault("competitors", [])
    filters.setdefault("languages", ["fr", "ar"])
    filters.setdefault("hashtags", [])
    filters.setdefault("period_days", 7)
    filters.setdefault("min_volume", 10)
    return filters


def _source_payload(client_id: str, source: dict[str, Any]) -> dict[str, Any] | None:
    channel = str(source.get("channel") or "").strip()
    url = str(source.get("url") or "").strip()
    label = str(source.get("label") or url).strip() or url
    if not url or channel not in _SUPPORTED_ADMIN_SOURCE_CHANNELS:
        return None

    mapping = {
        "facebook": ("managed_page", "token", {"fetch_mode": "collector", "page_url": url}),
        "instagram": ("instagram_profile", "token", {"fetch_mode": "collector", "profile_url": url}),
        "google_maps": ("public_reviews", "public", {"fetch_mode": "collector", "place_url": url}),
        "youtube": ("youtube_channel", "public", {"fetch_mode": "collector", "channel_url": url}),
        "import": ("batch_import", "file_upload", {"fetch_mode": "snapshot"}),
    }
    source_type, auth_mode, config_json = mapping[channel]
    return {
        "client_id": client_id,
        "source_name": label,
        "platform": channel,
        "source_type": source_type,
        "owner_type": "owned",
        "auth_mode": auth_mode,
        "config_json": config_json,
        "is_active": True,
        "sync_frequency_minutes": 60,
        "freshness_sla_hours": 24,
        "source_purpose": "owned_content",
        "source_priority": 1,
    }


def _pending_credentials(selected_sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    credentials: list[dict[str, Any]] = []
    seen: set[str] = set()
    mapping = {
        "facebook": ("oauth_access_token", "Credential Facebook requis pour activer la collecte admin."),
        "instagram": ("oauth_access_token", "Credential Instagram requis pour activer la collecte admin."),
        "youtube": ("api_key", "API key YouTube requise pour activer la collecte admin."),
        "google_maps": ("api_key", "API key Google Maps requise pour activer la collecte admin."),
    }
    for source in selected_sources:
        channel = str(source.get("channel") or "").strip()
        if channel not in mapping or channel in seen:
            continue
        seen.add(channel)
        credential_type, reason = mapping[channel]
        credentials.append(
            {
                "platform": channel,
                "credential_type": credential_type,
                "required": True,
                "reason": reason,
            }
        )
    return credentials


def confirm_onboarding(
    *,
    review_confirmed: bool,
    tenant_setup: dict[str, Any],
    brand_name: str,
    industry: str | None,
    selected_sources: list[dict[str, Any]],
    selected_channels: list[str],
    selected_watchlists: list[dict[str, Any]],
    selected_alert_profiles: list[dict[str, Any]],
    deferred_agent_config: list[dict[str, Any]],
) -> dict[str, Any]:
    if not review_confirmed:
        raise ValueError("review_confirmed must be true before confirm")

    brand = brand_name.strip()
    if not brand:
        raise ValueError("brand_name is required")

    normalized_channels = validate_requested_channels(_dedupe_channels(selected_channels))
    watch_seed, analysis_watchlists = _split_watchlists(selected_watchlists)

    client_name = str(tenant_setup.get("client_name") or brand).strip()
    client_slug = _slugify(str(tenant_setup.get("client_slug") or client_name))
    client = get_or_create_client(
        client_id=client_slug,
        client_name=client_name,
        industry=industry,
    )
    client_id = str(client["client_id"])
    set_active_client(client_id)

    watch_seed_filters = _merge_watch_seed_filters(
        watch_seed,
        brand_name=brand,
        selected_channels=normalized_channels,
        selected_sources=selected_sources,
    )
    watch_seed_watchlist_id = create_watchlist(
        name=str(watch_seed.get("name") or f"{client_name} watch seed").strip(),
        description=str(watch_seed.get("description") or "").strip(),
        scope_type="watch_seed",
        filters=watch_seed_filters,
        client_id=client_id,
    )

    watchlist_ids = [watch_seed_watchlist_id]
    for watchlist in analysis_watchlists:
        watchlist_ids.append(
            create_watchlist(
                name=str(watchlist.get("name") or "").strip(),
                description=str(watchlist.get("description") or "").strip(),
                scope_type=str(watchlist.get("scope_type") or "").strip(),
                filters=dict(watchlist.get("filters") or {}),
                client_id=client_id,
            )
        )

    orchestrator = IngestionOrchestrator()
    source_ids: list[str] = []
    for source in selected_sources:
        payload = _source_payload(client_id, source)
        if payload is None:
            continue
        created = orchestrator.create_source(payload)
        source_id = created.get("source_id")
        if source_id:
            source_ids.append(str(source_id))

    run = start_watch_run(
        client_id=client_id,
        watchlist_id=watch_seed_watchlist_id,
        requested_channels=normalized_channels,
    )

    return {
        "client_id": client_id,
        "watch_seed_watchlist_id": watch_seed_watchlist_id,
        "watchlist_id": watch_seed_watchlist_id,
        "watchlist_ids": watchlist_ids,
        "source_ids": source_ids,
        "requested_channels": normalized_channels,
        "pending_credentials": _pending_credentials(selected_sources),
        "pending_alert_profiles": selected_alert_profiles,
        "deferred_agent_config": deferred_agent_config,
        "run_id": run.get("run_id") if isinstance(run, dict) else None,
    }
