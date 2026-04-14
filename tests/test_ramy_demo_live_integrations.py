from __future__ import annotations

import sys
from pathlib import Path

import pytest

import config

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.demo.ramy_seed import (
    RAMY_FACEBOOK_PAGE_URL,
    RAMY_INSTAGRAM_PROFILE_URL,
    resolve_ramy_seed_dataset_path,
    seed_ramy_demo,
)
from api.data_loader import load_annotated
from core.onboarding.brand_discovery import discover_brand_signals
from core.onboarding.suggestion_engine import build_suggestions
from core.recommendation.agent_client import generate_recommendations
from core.recommendation.context_builder import build_recommendation_context
from core.runtime.env_doctor import assert_startup_ready, collect_startup_validation
from core.watch_runs.collectors.facebook_apify import collect_facebook_comments_apify
from core.watch_runs.collectors.instagram_apify import collect_instagram_comments_apify
from core.watch_runs.collectors.web_keyword import collect_web_keyword_results

pytestmark = [pytest.mark.integration]


@pytest.fixture(scope="module", autouse=True)
def seeded_demo_runtime() -> None:
    dataset_path = resolve_ramy_seed_dataset_path()
    seed_ramy_demo(
        csv_path=dataset_path,
        client_id="ramy-demo",
        client_name="Ramy Demo",
        reset=True,
    )


def test_env_doctor_passes_with_real_services() -> None:
    report = collect_startup_validation(
        public_urls=[RAMY_FACEBOOK_PAGE_URL, RAMY_INSTAGRAM_PROFILE_URL],
        timeout=10.0,
    )
    assert_startup_ready(report)


def test_serpapi_brand_discovery_returns_real_signals() -> None:
    signals = discover_brand_signals(
        brand_name="Ramy",
        country="dz",
        product_name="jus",
    )

    assert signals["skipped"] is False
    assert signals["organic"]


def test_openai_onboarding_suggestions_are_generated_from_real_discovery() -> None:
    serp_signals = discover_brand_signals(
        brand_name="Ramy",
        country="dz",
        product_name="jus",
    )

    result = build_suggestions(
        brand_name="Ramy",
        product_name="jus",
        serp_signals=serp_signals,
    )

    assert result["fallback_used"] is False
    assert result["suggested_sources"]
    assert result["suggested_watchlists"]


def test_tavily_web_search_returns_real_documents() -> None:
    documents = collect_web_keyword_results(
        client_id="ramy-demo",
        keywords=["ramy jus algerie"],
        max_results=3,
    )

    assert isinstance(documents, list)
    assert documents
    assert str(documents[0]["source_url"]).startswith("https://")


def test_facebook_apify_live_collection_returns_documents() -> None:
    documents = collect_facebook_comments_apify(
        client_id="ramy-demo",
        seed_urls=[RAMY_FACEBOOK_PAGE_URL],
        max_posts=2,
        max_comments_per_post=5,
        delay_between_calls=0.0,
    )

    assert isinstance(documents, list)
    assert documents
    assert str(documents[0]["source_url"]).startswith("https://")


def test_instagram_apify_live_collection_returns_documents() -> None:
    documents = collect_instagram_comments_apify(
        client_id="ramy-demo",
        seed_urls=[RAMY_INSTAGRAM_PROFILE_URL],
        max_posts=2,
        max_comments_per_post=5,
        delay_between_calls=0.0,
    )

    if isinstance(documents, dict):
        assert documents == {"status": "skipped", "documents": [], "reason": "no_public_posts"}
        return

    assert isinstance(documents, list)
    assert documents
    assert str(documents[0]["source_url"]).startswith("https://")


def test_configured_recommendations_are_generated_on_seeded_context() -> None:
    annotated = load_annotated(client_id="ramy-demo", ttl=0)
    context = build_recommendation_context(
        "manual",
        None,
        annotated,
        client_id="ramy-demo",
    )

    result = generate_recommendations(
        context,
        provider=config.DEFAULT_AGENT_PROVIDER,
        model=config.DEFAULT_AGENT_MODEL,
    )

    assert result["provider_used"] == config.DEFAULT_AGENT_PROVIDER
    assert result["model_used"] == config.DEFAULT_AGENT_MODEL
    assert result["parse_success"] is True
    assert result["recommendations"]
    assert result["analysis_summary"]
