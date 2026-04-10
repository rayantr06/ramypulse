from __future__ import annotations

import importlib
import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest


def _import_module(module_name: str):
    return importlib.import_module(module_name)


class TestBrandWatchlist:
    def test_defaults(self) -> None:
        module = _import_module("core.discovery.brand_watchlist")
        watchlist = module.BrandWatchlist()

        assert watchlist.brand_name == "Ramy"
        assert "رامي" in watchlist.brand_variants
        assert len(watchlist.priority_domains) == 7
        assert watchlist.monthly_budget_usd == 5.0

    def test_budget_split_sums_to_one(self) -> None:
        module = _import_module("core.discovery.brand_watchlist")
        watchlist = module.BrandWatchlist()

        assert abs(sum(watchlist.budget_split.values()) - 1.0) < 0.001


class TestQueryPlanner:
    def test_generates_queries_press(self) -> None:
        brand_watchlist = _import_module("core.discovery.brand_watchlist")
        query_planner = _import_module("core.discovery.query_planner")

        planner = query_planner.QueryPlanner(brand_watchlist.BrandWatchlist())
        queries = planner.generate_queries("press", max_queries=5)

        assert 1 <= len(queries) <= 5
        assert all(isinstance(query, str) for query in queries)

    def test_discovery_includes_competitor_queries(self) -> None:
        brand_watchlist = _import_module("core.discovery.brand_watchlist")
        query_planner = _import_module("core.discovery.query_planner")

        planner = query_planner.QueryPlanner(brand_watchlist.BrandWatchlist())
        queries = planner.generate_queries("discovery", max_queries=20)

        assert any("vs" in query for query in queries)

    def test_domains_and_recency_follow_mode(self) -> None:
        brand_watchlist = _import_module("core.discovery.brand_watchlist")
        query_planner = _import_module("core.discovery.query_planner")

        planner = query_planner.QueryPlanner(brand_watchlist.BrandWatchlist())

        assert "echoroukonline.com" in planner.get_domains("press")
        assert planner.get_domains("reddit") == ["reddit.com"]
        assert planner.get_domains("discovery") is None
        assert planner.get_recency("press") == "week"
        assert planner.get_recency("reddit") == "month"

    def test_respects_max_queries(self) -> None:
        brand_watchlist = _import_module("core.discovery.brand_watchlist")
        query_planner = _import_module("core.discovery.query_planner")

        planner = query_planner.QueryPlanner(brand_watchlist.BrandWatchlist())
        queries = planner.generate_queries("press", max_queries=3)

        assert len(queries) <= 3


class TestBudgetController:
    def test_can_spend_within_budget(self, tmp_path: Path) -> None:
        module = _import_module("core.discovery.budget_controller")
        budget = module.BudgetController(
            monthly_budget_usd=5.0,
            state_path=str(tmp_path / "budget.json"),
        )

        assert budget.can_spend("press", n_search=1)

    def test_blocks_when_exhausted(self, tmp_path: Path) -> None:
        module = _import_module("core.discovery.budget_controller")
        budget = module.BudgetController(
            monthly_budget_usd=0.01,
            state_path=str(tmp_path / "budget.json"),
        )

        budget.record_spend("press", n_search=2)

        assert not budget.can_spend("press", n_search=1)

    def test_mode_isolation(self, tmp_path: Path) -> None:
        module = _import_module("core.discovery.budget_controller")
        budget = module.BudgetController(
            monthly_budget_usd=1.0,
            budget_split={"press": 0.5, "reddit": 0.5},
            state_path=str(tmp_path / "budget.json"),
        )

        for _ in range(100):
            budget.record_spend("press", n_search=1)

        assert not budget.can_spend("press", n_search=1)
        assert budget.can_spend("reddit", n_search=1)

    def test_persists_state(self, tmp_path: Path) -> None:
        module = _import_module("core.discovery.budget_controller")
        state_file = tmp_path / "budget.json"
        budget = module.BudgetController(
            monthly_budget_usd=5.0,
            state_path=str(state_file),
        )

        budget.record_spend("press", n_search=5)
        payload = json.loads(state_file.read_text())

        assert payload["search_calls"] == 5
        assert abs(payload["total_cost_usd"] - 0.025) < 0.0001

    def test_max_queries_for_mode(self, tmp_path: Path) -> None:
        module = _import_module("core.discovery.budget_controller")
        budget = module.BudgetController(
            monthly_budget_usd=5.0,
            state_path=str(tmp_path / "budget.json"),
        )

        assert budget.max_queries_for_mode("press") == 500

    def test_monthly_reset(self, tmp_path: Path) -> None:
        module = _import_module("core.discovery.budget_controller")
        state_file = tmp_path / "budget.json"
        state_file.write_text(
            json.dumps(
                {
                    "month": "2025-01",
                    "search_calls": 999,
                    "fetch_calls": 0,
                    "total_cost_usd": 4.99,
                    "by_mode": {"press": 2.5, "reddit": 1.0, "discovery": 1.49},
                }
            )
        )

        budget = module.BudgetController(
            monthly_budget_usd=5.0,
            state_path=str(state_file),
        )

        assert budget.can_spend("press", n_search=1)
        assert budget.get_remaining() == 5.0


class TestPerplexityCollector:
    MOCK_RESPONSE = {
        "results": [
            {
                "title": "Ramy lance une nouvelle gamme bio",
                "url": "https://tsa-algerie.com/ramy-bio-2026/",
                "snippet": "Le groupe Ramy a annonce le lancement d'une gamme bio.",
                "date": "2026-04-08",
            },
            {
                "title": "Avis sur Ramy jus",
                "url": "https://reddit.com/r/algeria/comments/abc123",
                "snippet": "Ramy c'est le meilleur jus en Algerie wallah.",
                "date": "2026-04-07",
            },
        ],
        "id": "req_test123",
    }

    def _mock_post(self, *args, **kwargs):
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = self.MOCK_RESPONSE
        response.raise_for_status = MagicMock()
        return response

    def _isolate_budget_state(self, module, monkeypatch, tmp_path: Path) -> None:
        real_budget_controller = module.BudgetController

        class _IsolatedBudgetController(real_budget_controller):
            def __init__(self, *args, **kwargs):
                kwargs.setdefault("state_path", str(tmp_path / "budget_state.json"))
                super().__init__(*args, **kwargs)

        monkeypatch.setattr(module, "BudgetController", _IsolatedBudgetController)

    def test_collect_discovery_returns_watch_documents(self, monkeypatch, tmp_path: Path) -> None:
        module = _import_module("core.watch_runs.collectors.perplexity_discovery")
        self._isolate_budget_state(module, monkeypatch, tmp_path)
        monkeypatch.setattr(module.config, "PERPLEXITY_API_KEY", "pplx-test-key", raising=False)
        monkeypatch.setattr(module.requests, "post", self._mock_post)

        result = module.collect_perplexity_discovery(client_id="ramy_client_001")

        assert isinstance(result, list)
        assert len(result) > 0
        assert result[0]["raw_payload"]["discovery_brain"] is True
        assert "external_document_id" in result[0]
        assert "raw_metadata" in result[0]

    def test_collect_press_returns_documents(self, monkeypatch, tmp_path: Path) -> None:
        module = _import_module("core.watch_runs.collectors.perplexity_discovery")
        self._isolate_budget_state(module, monkeypatch, tmp_path)
        monkeypatch.setattr(module.config, "PERPLEXITY_API_KEY", "pplx-test-key", raising=False)
        monkeypatch.setattr(module.requests, "post", self._mock_post)

        result = module.collect_perplexity_press(client_id="ramy_client_001")

        assert isinstance(result, list)

    def test_skips_without_api_key(self, monkeypatch, tmp_path: Path) -> None:
        module = _import_module("core.watch_runs.collectors.perplexity_discovery")
        self._isolate_budget_state(module, monkeypatch, tmp_path)
        monkeypatch.setattr(module.config, "PERPLEXITY_API_KEY", "", raising=False)

        result = module.collect_perplexity_discovery(client_id="ramy_client_001")

        assert result == {"status": "skipped", "documents": [], "reason": "missing_api_key"}

    def test_api_uses_query_singular_not_queries(self, monkeypatch, tmp_path: Path) -> None:
        module = _import_module("core.watch_runs.collectors.perplexity_discovery")
        self._isolate_budget_state(module, monkeypatch, tmp_path)
        monkeypatch.setattr(module.config, "PERPLEXITY_API_KEY", "pplx-test-key", raising=False)

        calls: list[dict[str, object]] = []

        def _capture_post(*args, **kwargs):
            calls.append(kwargs)
            return self._mock_post(*args, **kwargs)

        monkeypatch.setattr(module.requests, "post", _capture_post)

        module.collect_perplexity_discovery(client_id="ramy_client_001")

        assert calls
        for call in calls:
            body = call["json"]
            assert "query" in body
            assert isinstance(body["query"], str)
            assert "queries" not in body

    def test_deduplicates_urls(self, monkeypatch, tmp_path: Path) -> None:
        module = _import_module("core.watch_runs.collectors.perplexity_discovery")
        self._isolate_budget_state(module, monkeypatch, tmp_path)
        monkeypatch.setattr(module.config, "PERPLEXITY_API_KEY", "pplx-test-key", raising=False)
        monkeypatch.setattr(module.requests, "post", self._mock_post)

        result = module.collect_perplexity_discovery(client_id="ramy_client_001")

        urls = [document["source_url"] for document in result]
        assert len(urls) == len(set(urls))

    def test_channel_attribution_uses_result_url(self, monkeypatch, tmp_path: Path) -> None:
        module = _import_module("core.watch_runs.collectors.perplexity_discovery")
        self._isolate_budget_state(module, monkeypatch, tmp_path)
        monkeypatch.setattr(module.config, "PERPLEXITY_API_KEY", "pplx-test-key", raising=False)
        monkeypatch.setattr(module.requests, "post", self._mock_post)

        result = module.collect_perplexity_discovery(client_id="ramy_client_001")

        channels = {document["raw_metadata"]["channel"] for document in result}
        assert "press" in channels or "reddit" in channels


class TestRunServiceIntegration:
    def test_default_collectors_has_press(self) -> None:
        module = _import_module("core.watch_runs.run_service")
        assert "press" in module.DEFAULT_COLLECTORS

    def test_default_collectors_has_reddit(self) -> None:
        module = _import_module("core.watch_runs.run_service")
        assert "reddit" in module.DEFAULT_COLLECTORS

    def test_web_search_points_to_perplexity(self) -> None:
        run_service = _import_module("core.watch_runs.run_service")
        collector = _import_module("core.watch_runs.collectors.perplexity_discovery")

        assert run_service.DEFAULT_COLLECTORS["web_search"] is collector.collect_perplexity_discovery

    def test_validate_requested_channels_accepts_new_channels(self) -> None:
        module = _import_module("core.watch_runs.run_service")
        result = module.validate_requested_channels(["press", "reddit", "web_search"])

        assert result == ["press", "reddit", "web_search"]
