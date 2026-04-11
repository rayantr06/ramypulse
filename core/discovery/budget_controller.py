"""Budget controls for Discovery Brain V1 Perplexity usage."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

SEARCH_COST_PER_REQ = 0.005
FETCH_COST_PER_REQ = 0.0005


class BudgetController:
    """Track and enforce monthly spend for discovery modes."""

    def __init__(
        self,
        monthly_budget_usd: float = 5.0,
        budget_split: dict[str, float] | None = None,
        state_path: str = "data/budget_state.json",
    ):
        self.monthly_budget = monthly_budget_usd
        self.budget_split = budget_split or {
            "press": 0.50,
            "reddit": 0.20,
            "discovery": 0.30,
        }
        self.state_path = Path(state_path)
        self._state = self._load_state()

    def _current_month(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m")

    def _new_state(self) -> dict[str, object]:
        return {
            "month": self._current_month(),
            "search_calls": 0,
            "fetch_calls": 0,
            "total_cost_usd": 0.0,
            "by_mode": {"press": 0.0, "reddit": 0.0, "discovery": 0.0},
        }

    def _load_state(self) -> dict[str, object]:
        if self.state_path.exists():
            with self.state_path.open(encoding="utf-8") as handle:
                state = json.load(handle)
            if state.get("month") != self._current_month():
                return self._new_state()
            return state
        return self._new_state()

    def _save_state(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        with self.state_path.open("w", encoding="utf-8") as handle:
            json.dump(self._state, handle, indent=2)

    def can_spend(self, mode: str, n_search: int = 1, n_fetch: int = 0) -> bool:
        cost = (n_search * SEARCH_COST_PER_REQ) + (n_fetch * FETCH_COST_PER_REQ)
        mode_budget = self.monthly_budget * self.budget_split.get(mode, 0.0)
        mode_spent = float((self._state.get("by_mode") or {}).get(mode, 0.0))
        total_spent = float(self._state.get("total_cost_usd") or 0.0)

        if mode_spent + cost > mode_budget:
            logger.warning(
                "BudgetController: budget %s exhausted ($%.3f / $%.3f)",
                mode,
                mode_spent,
                mode_budget,
            )
            return False
        if total_spent + cost > self.monthly_budget:
            logger.warning(
                "BudgetController: total budget exhausted ($%.3f / $%.2f)",
                total_spent,
                self.monthly_budget,
            )
            return False
        return True

    def record_spend(self, mode: str, n_search: int = 0, n_fetch: int = 0) -> None:
        cost = (n_search * SEARCH_COST_PER_REQ) + (n_fetch * FETCH_COST_PER_REQ)
        self._state["search_calls"] = int(self._state.get("search_calls") or 0) + n_search
        self._state["fetch_calls"] = int(self._state.get("fetch_calls") or 0) + n_fetch
        self._state["total_cost_usd"] = float(self._state.get("total_cost_usd") or 0.0) + cost
        by_mode = dict(self._state.get("by_mode") or {})
        by_mode[mode] = float(by_mode.get(mode, 0.0)) + cost
        self._state["by_mode"] = by_mode
        self._save_state()
        logger.info(
            "BudgetController: +$%.4f (%s) total=$%.3f / $%.2f",
            cost,
            mode,
            self._state["total_cost_usd"],
            self.monthly_budget,
        )

    def get_remaining(self, mode: str | None = None) -> float:
        if mode:
            mode_budget = self.monthly_budget * self.budget_split.get(mode, 0.0)
            return mode_budget - float((self._state.get("by_mode") or {}).get(mode, 0.0))
        return self.monthly_budget - float(self._state.get("total_cost_usd") or 0.0)

    def max_queries_for_mode(self, mode: str) -> int:
        remaining = self.get_remaining(mode)
        return max(0, int(remaining / SEARCH_COST_PER_REQ))
