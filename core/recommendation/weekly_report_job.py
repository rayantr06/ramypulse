"""Job hebdomadaire de generation et de delivery des recommandations."""

from __future__ import annotations

import importlib
import logging

import pandas as pd

import config
import core.recommendation.agent_client as agent_client
import core.recommendation.context_builder as context_builder
from core.notifications.notification_manager import (
    send_email_notification,
    send_slack_notification,
)
from core.recommendation.recommendation_manager import (
    get_client_agent_config,
    get_recommendation,
    save_recommendation,
)
from core.security.secret_manager import resolve_secret

logger = logging.getLogger(__name__)


def _config_module():
    """Retourne le module config courant, meme apres reload dans les tests."""
    return importlib.import_module("config")


def should_run_weekly_report(current_date: pd.Timestamp, weekly_report_day: int) -> bool:
    """Indique si la date courante correspond au jour configure."""
    return int(current_date.isoweekday()) == int(weekly_report_day)


def _format_weekly_report_message(recommendation: dict) -> str:
    """Construit un message synthetique exploitable pour les canaux de delivery."""
    recommendations = recommendation.get("recommendations", [])
    titles = [str(item.get("title", "")).strip() for item in recommendations[:3] if item.get("title")]
    lines = [recommendation.get("analysis_summary") or "Rapport hebdomadaire RamyPulse"]
    if titles:
        lines.append("")
        lines.append("Priorites:")
        lines.extend(f"- {title}" for title in titles)
    return "\n".join(lines).strip()


def run_weekly_recommendation_job(
    df_annotated: pd.DataFrame,
    current_date: pd.Timestamp | None = None,
    client_id: str = config.DEFAULT_CLIENT_ID,
) -> dict | None:
    """Genere le rapport hebdomadaire si la configuration client l'autorise."""
    cfg = _config_module()
    now = pd.Timestamp(current_date or pd.Timestamp.now())
    agent_config = get_client_agent_config(client_id=client_id)
    if not agent_config.get("weekly_report_enabled"):
        return None
    if not should_run_weekly_report(now, int(agent_config.get("weekly_report_day") or 1)):
        return None

    context = context_builder.build_recommendation_context(
        trigger_type="scheduled",
        trigger_id=None,
        df_annotated=df_annotated,
        max_rag_chunks=8,
    )
    result = agent_client.generate_recommendations(
        context=context,
        provider=agent_config.get("provider") or cfg.DEFAULT_AGENT_PROVIDER,
        model=agent_config.get("model"),
        api_key=resolve_secret(agent_config.get("api_key_encrypted")),
    )
    result["context_tokens"] = context.get("estimated_tokens")
    recommendation_id = save_recommendation(
        result=result,
        trigger_type="scheduled",
        trigger_id=None,
        client_id=client_id,
    )
    recommendation = get_recommendation(recommendation_id)
    if recommendation is None:
        raise RuntimeError("Recommendation hebdomadaire introuvable apres sauvegarde")

    message = _format_weekly_report_message(recommendation)
    email_recipient = getattr(cfg, "WEEKLY_REPORT_EMAIL_TO", "")
    slack_reference = getattr(cfg, "WEEKLY_REPORT_SLACK_WEBHOOK_REFERENCE", "")

    if email_recipient:
        send_email_notification(
            title="RamyPulse - Rapport hebdomadaire",
            message=message,
            recipient=email_recipient,
            reference_id=recommendation_id,
        )
    if resolve_secret(slack_reference):
        send_slack_notification(
            title="RamyPulse - Rapport hebdomadaire",
            message=message,
            webhook_url=slack_reference,
            reference_id=recommendation_id,
        )

    logger.info("Rapport hebdomadaire genere: %s", recommendation_id)
    return recommendation
