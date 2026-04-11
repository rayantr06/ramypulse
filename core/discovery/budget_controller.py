"""Controle budgetaire pour l'usage Perplexity de Discovery Brain V1."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import config

logger = logging.getLogger(__name__)

SEARCH_COST_PER_REQ = 0.005
FETCH_COST_PER_REQ = 0.0005


class BudgetController:
    """Suit et controle la depense mensuelle par mode de decouverte."""

    def __init__(
        self,
        monthly_budget_usd: float = 5.0,
        budget_split: dict[str, float] | None = None,
        state_path: str | Path | None = None,
    ):
        """Initialise le controleur avec un budget et un chemin d'etat."""
        self.monthly_budget = monthly_budget_usd
        self.budget_split = budget_split or {
            "press": 0.50,
            "reddit": 0.20,
            "discovery": 0.30,
        }
        self.state_path = Path(state_path) if state_path is not None else config.DATA_DIR / "budget_state.json"
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

    def _write_state(self, state: dict[str, object]) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        with self.state_path.open("w", encoding="utf-8") as handle:
            json.dump(state, handle, indent=2)

    def _load_state(self) -> dict[str, object]:
        if self.state_path.exists():
            with self.state_path.open(encoding="utf-8") as handle:
                state = json.load(handle)
            if state.get("month") != self._current_month():
                fresh_state = self._new_state()
                self._write_state(fresh_state)
                return fresh_state
            return state
        return self._new_state()

    def _save_state(self) -> None:
        """Persiste l'etat courant sur disque."""
        self._write_state(self._state)

    def can_spend(self, mode: str, n_search: int = 1, n_fetch: int = 0) -> bool:
        """Indique si une depense supplementaire reste dans les limites du budget."""
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
        """Enregistre une depense effective apres un appel API reussi."""
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
        """Retourne le budget restant globalement ou pour un mode donne."""
        if mode:
            mode_budget = self.monthly_budget * self.budget_split.get(mode, 0.0)
            return mode_budget - float((self._state.get("by_mode") or {}).get(mode, 0.0))
        return self.monthly_budget - float(self._state.get("total_cost_usd") or 0.0)

    def max_queries_for_mode(self, mode: str) -> int:
        """Calcule le nombre maximum de requetes Search restantes pour un mode."""
        remaining = self.get_remaining(mode)
        return max(0, int(remaining / SEARCH_COST_PER_REQ))
