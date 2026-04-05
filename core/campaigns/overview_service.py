"""Agrégation métier pour la page Campagnes."""

from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime
from typing import Any

from core.campaigns import campaign_manager
from core.social_metrics import metrics_aggregator


def _parse_campaign_date(value: str | None) -> date | None:
    if not value:
        return None

    candidate = str(value).strip()
    if not candidate:
        return None

    try:
        return datetime.fromisoformat(candidate.replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return date.fromisoformat(candidate[:10])
        except ValueError:
            return None


def _quarter_bounds(today: date | None = None) -> tuple[date, date, str]:
    current = today or date.today()
    quarter_start_month = ((current.month - 1) // 3) * 3 + 1
    quarter_end_month = quarter_start_month + 2
    start = date(current.year, quarter_start_month, 1)
    end = date(current.year, quarter_end_month, monthrange(current.year, quarter_end_month)[1])
    quarter_index = ((quarter_start_month - 1) // 3) + 1
    return start, end, f"T{quarter_index} {current.year}"


def _campaign_reference_date(campaign: dict[str, Any]) -> date | None:
    return _parse_campaign_date(campaign.get("start_date"))


def _quarter_campaigns(campaigns: list[dict[str, Any]], today: date | None = None) -> tuple[list[dict[str, Any]], str]:
    quarter_start, quarter_end, quarter_label = _quarter_bounds(today)
    quarter_campaigns: list[dict[str, Any]] = []

    for campaign in campaigns:
        reference_date = _campaign_reference_date(campaign)
        if reference_date is None:
            continue
        if not (quarter_start <= reference_date <= quarter_end):
            continue
        if campaign.get("status") == "cancelled":
            continue
        budget = campaign.get("budget_dza")
        if budget in (None, ""):
            continue
        quarter_campaigns.append(campaign)

    return quarter_campaigns, quarter_label


def get_quarter_budget_stats(today: date | None = None) -> dict[str, Any]:
    campaigns = campaign_manager.list_campaigns(limit=1000)
    quarter_campaigns, quarter_label = _quarter_campaigns(campaigns, today)

    quarterly_budget_allocation = sum(
        int(campaign.get("budget_dza") or 0) for campaign in quarter_campaigns
    )
    quarterly_budget_committed = sum(
        int(campaign.get("budget_dza") or 0)
        for campaign in quarter_campaigns
        if campaign.get("status") in {"active", "completed"}
    )

    return {
        "quarterly_budget_committed": quarterly_budget_committed,
        "quarterly_budget_allocation": quarterly_budget_allocation,
        "quarter_label": quarter_label,
        "quarter_campaigns": quarter_campaigns,
    }


def _candidate_scope(campaigns: list[dict[str, Any]], quarter_campaigns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    active_campaigns = [campaign for campaign in campaigns if campaign.get("status") == "active"]
    if active_campaigns:
        return active_campaigns
    if quarter_campaigns:
        return quarter_campaigns
    return campaigns


def _performance_payload(campaign: dict[str, Any]) -> dict[str, Any]:
    summary = metrics_aggregator.get_campaign_engagement(campaign["campaign_id"])
    if "error" in summary:
        summary = {}

    totals = summary.get("totals", {}) if isinstance(summary, dict) else {}
    total_interactions = (
        int(totals.get("likes", 0))
        + int(totals.get("comments", 0))
        + int(totals.get("shares", 0))
    )

    return {
        "campaign_id": campaign["campaign_id"],
        "campaign_name": campaign.get("campaign_name"),
        "influencer_handle": campaign.get("influencer_handle"),
        "platform": campaign.get("platform"),
        "status": campaign.get("status"),
        "budget_dza": campaign.get("budget_dza"),
        "roi_pct": summary.get("roi_pct"),
        "engagement_rate": summary.get("engagement_rate"),
        "signal_count": int(summary.get("signal_count", 0) or 0),
        "sentiment_breakdown": dict(summary.get("sentiment_breakdown", {}) or {}),
        "negative_aspects": list(summary.get("negative_aspects", []) or []),
        "_total_interactions": total_interactions,
    }


def _selection_basis(candidates: list[dict[str, Any]]) -> str:
    if any(candidate.get("roi_pct") is not None for candidate in candidates):
        return "roi_pct"
    if any(candidate.get("engagement_rate") is not None for candidate in candidates):
        return "engagement_rate"
    if any(int(candidate.get("_total_interactions", 0) or 0) > 0 for candidate in candidates):
        return "total_interactions"
    if any(int(candidate.get("signal_count", 0) or 0) > 0 for candidate in candidates):
        return "signal_count"
    if any(int(candidate.get("budget_dza") or 0) > 0 for candidate in candidates):
        return "budget_dza"
    return "fallback"


def _candidate_sort_key(candidate: dict[str, Any], basis: str) -> tuple[Any, ...]:
    primary_value = {
        "roi_pct": candidate.get("roi_pct") if candidate.get("roi_pct") is not None else float("-inf"),
        "engagement_rate": candidate.get("engagement_rate") if candidate.get("engagement_rate") is not None else float("-inf"),
        "total_interactions": int(candidate.get("_total_interactions", 0) or 0),
        "signal_count": int(candidate.get("signal_count", 0) or 0),
        "budget_dza": int(candidate.get("budget_dza") or 0),
        "fallback": int(candidate.get("budget_dza") or 0),
    }[basis]

    return (
        primary_value,
        int(candidate.get("_total_interactions", 0) or 0),
        int(candidate.get("signal_count", 0) or 0),
        int(candidate.get("budget_dza") or 0),
        str(candidate.get("campaign_name") or ""),
    )


def _public_top_performer(candidate: dict[str, Any], basis: str) -> dict[str, Any]:
    return {
        "campaign_id": candidate.get("campaign_id"),
        "campaign_name": candidate.get("campaign_name"),
        "influencer_handle": candidate.get("influencer_handle"),
        "platform": candidate.get("platform"),
        "status": candidate.get("status"),
        "budget_dza": candidate.get("budget_dza"),
        "roi_pct": candidate.get("roi_pct"),
        "engagement_rate": candidate.get("engagement_rate"),
        "signal_count": candidate.get("signal_count", 0),
        "sentiment_breakdown": candidate.get("sentiment_breakdown", {}),
        "negative_aspects": candidate.get("negative_aspects", []),
        "selection_basis": basis,
    }


def get_campaigns_overview(today: date | None = None) -> dict[str, Any]:
    campaigns = campaign_manager.list_campaigns(limit=1000)
    stats = get_quarter_budget_stats(today=today)
    candidates_scope = _candidate_scope(campaigns, stats["quarter_campaigns"])

    top_performer = None
    if candidates_scope:
        candidate_payloads = [_performance_payload(campaign) for campaign in candidates_scope]
        basis = _selection_basis(candidate_payloads)
        best_candidate = max(candidate_payloads, key=lambda candidate: _candidate_sort_key(candidate, basis))
        top_performer = _public_top_performer(best_candidate, basis)

    return {
        "quarterly_budget_committed": stats["quarterly_budget_committed"],
        "quarterly_budget_allocation": stats["quarterly_budget_allocation"],
        "quarter_label": stats["quarter_label"],
        "active_campaigns_count": sum(1 for campaign in campaigns if campaign.get("status") == "active"),
        "top_performer": top_performer,
    }
