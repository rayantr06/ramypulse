"""Calculateur d'impact de campagne RamyPulse.

Implémente les trois fenêtres pré/active/post et le score d'attribution.
Signatures conformes à INTERFACES.md Section 4.1.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timedelta
from uuid import uuid4

import pandas as pd

import config
from config import DEFAULT_POST_WINDOW_DAYS, DEFAULT_PRE_WINDOW_DAYS, MIN_SIGNALS_FOR_ATTRIBUTION
from core.alerts.alert_manager import create_alert
from core.campaigns.campaign_manager import get_campaign

logger = logging.getLogger(__name__)


_DDL_CAMPAIGN_METRICS_SNAPSHOTS = """
CREATE TABLE IF NOT EXISTS campaign_metrics_snapshots (
    snapshot_id         TEXT PRIMARY KEY,
    campaign_id         TEXT NOT NULL,
    phase               TEXT NOT NULL,
    metric_date         TEXT NOT NULL,
    nss_filtered        REAL,
    nss_baseline        REAL,
    nss_uplift          REAL,
    volume_filtered     INTEGER DEFAULT 0,
    volume_baseline     INTEGER DEFAULT 0,
    volume_lift_pct     REAL,
    aspect_breakdown    TEXT DEFAULT '{}',
    sentiment_breakdown TEXT DEFAULT '{}',
    computed_at         TEXT NOT NULL,
    UNIQUE(campaign_id, phase, metric_date)
)
"""

_DDL_CAMPAIGN_SIGNAL_LINKS = """
CREATE TABLE IF NOT EXISTS campaign_signal_links (
    link_id             TEXT PRIMARY KEY,
    campaign_id         TEXT NOT NULL,
    signal_id           TEXT NOT NULL,
    phase               TEXT NOT NULL,
    attribution_score   REAL,
    attributed_at       TEXT NOT NULL
)
"""


def _get_connection() -> sqlite3.Connection:
    """Ouvre une connexion SQLite courte duree pour les artefacts campagne."""
    connection = sqlite3.connect(str(config.SQLITE_DB_PATH))
    connection.row_factory = sqlite3.Row
    connection.execute(_DDL_CAMPAIGN_METRICS_SNAPSHOTS)
    connection.execute(_DDL_CAMPAIGN_SIGNAL_LINKS)
    connection.commit()
    return connection


def _now() -> str:
    """Retourne un timestamp ISO courant."""
    return datetime.now().isoformat()


def _new_id() -> str:
    """Genere un identifiant UUID textuel."""
    return str(uuid4())


def _parse_datetime_bound(value: str, *, inclusive_end: bool) -> pd.Timestamp:
    """Parse une borne temporelle et etend les dates seules a la journee complete."""
    parsed = pd.to_datetime(value)
    if "T" not in value and " " not in value:
        return parsed + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1) if inclusive_end else parsed
    return parsed


# ---------------------------------------------------------------------------
# Fonctions de filtrage
# ---------------------------------------------------------------------------


def filter_signals_for_campaign(
    df: pd.DataFrame,
    campaign: dict,
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    """Filtre le DataFrame selon les dimensions de la campagne dans une fenêtre temporelle.

    Filtres appliqués (AND logique, champ ignoré si None/vide) :
    - timestamp entre start_date et end_date
    - channel == campaign["platform"] (si platform != "multi_platform")
    - aspect in campaign["target_aspects"] (si non vide)
    - wilaya in campaign["target_regions"] (si non vide)
    - text contient au moins 1 keyword de campaign["keywords"] (si non vide)

    Returns: DataFrame filtré, peut être vide.
    """
    if df.empty:
        return df.copy()

    try:
        start_dt = _parse_datetime_bound(start_date, inclusive_end=False)
        end_dt = _parse_datetime_bound(end_date, inclusive_end=True)
    except Exception:
        logger.warning("Dates invalides dans filter_signals_for_campaign : %s / %s", start_date, end_date)
        return pd.DataFrame()

    result = df.copy()

    # Filtre temporel
    if "timestamp" in result.columns:
        ts = pd.to_datetime(result["timestamp"], errors="coerce")
        result = result[ts.between(start_dt, end_dt)]

    if result.empty:
        return result

    # Filtre platform (channel)
    platform = campaign.get("platform")
    if platform and platform != "multi_platform" and "channel" in result.columns:
        result = result[result["channel"] == platform]

    if result.empty:
        return result

    # Filtre aspects
    target_aspects = campaign.get("target_aspects") or []
    if target_aspects and "aspect" in result.columns:
        result = result[result["aspect"].isin(target_aspects)]

    if result.empty:
        return result

    # Filtre wilayas
    target_regions = campaign.get("target_regions") or []
    if target_regions and "wilaya" in result.columns:
        result = result[result["wilaya"].isin(target_regions)]

    if result.empty:
        return result

    # Filtre keywords dans le texte
    keywords = campaign.get("keywords") or []
    if keywords and "text" in result.columns:
        kw_lower = [k.lower() for k in keywords]
        mask = result["text"].apply(
            lambda t: any(kw in str(t).lower() for kw in kw_lower) if pd.notna(t) else False
        )
        result = result[mask]

    return result


# ---------------------------------------------------------------------------
# Calculs de métriques NSS
# ---------------------------------------------------------------------------


def _compute_nss(df: pd.DataFrame) -> float | None:
    """Calcule le NSS sur un DataFrame de signaux."""
    if df.empty or "sentiment_label" not in df.columns:
        return None
    total = len(df)
    if total == 0:
        return None
    pos = int(df["sentiment_label"].isin(["très_positif", "positif"]).sum())
    neg = int(df["sentiment_label"].isin(["très_négatif", "négatif"]).sum())
    return round((pos - neg) / total * 100, 2)


def _aspect_breakdown(df: pd.DataFrame) -> dict:
    """Calcule le NSS par aspect sur un DataFrame."""
    if df.empty or "aspect" not in df.columns:
        return {}
    result = {}
    for aspect in df["aspect"].dropna().unique():
        if not aspect:
            continue
        sub = df[df["aspect"] == aspect]
        nss = _compute_nss(sub)
        if nss is not None:
            result[str(aspect)] = nss
    return result


def _sentiment_breakdown(df: pd.DataFrame) -> dict:
    """Compte les occurrences de chaque label de sentiment."""
    labels = ["très_positif", "positif", "neutre", "négatif", "très_négatif"]
    if df.empty or "sentiment_label" not in df.columns:
        return {label: 0 for label in labels}
    counts = df["sentiment_label"].value_counts()
    return {label: int(counts.get(label, 0)) for label in labels}


def _phase_metrics(df: pd.DataFrame) -> dict:
    """Calcule les métriques (nss, volume, breakdowns) pour une phase."""
    return {
        "nss": _compute_nss(df),
        "volume": len(df),
        "aspect_breakdown": _aspect_breakdown(df),
        "sentiment_breakdown": _sentiment_breakdown(df),
    }


def _persist_campaign_snapshot(
    connection: sqlite3.Connection,
    campaign_id: str,
    phase: str,
    metrics: dict,
    baseline_metrics: dict,
    metric_date: str,
    computed_at: str,
) -> None:
    """Persiste un snapshot de métriques pour une phase de campagne."""
    baseline_nss = baseline_metrics.get("nss")
    baseline_volume = int(baseline_metrics.get("volume", 0) or 0)
    current_nss = metrics.get("nss")
    current_volume = int(metrics.get("volume", 0) or 0)

    nss_uplift = None
    if current_nss is not None and baseline_nss is not None:
        nss_uplift = round(float(current_nss) - float(baseline_nss), 2)

    volume_lift_pct = None
    if baseline_volume > 0:
        volume_lift_pct = round(((current_volume - baseline_volume) / baseline_volume) * 100.0, 2)

    connection.execute(
        """
        INSERT OR REPLACE INTO campaign_metrics_snapshots (
            snapshot_id,
            campaign_id,
            phase,
            metric_date,
            nss_filtered,
            nss_baseline,
            nss_uplift,
            volume_filtered,
            volume_baseline,
            volume_lift_pct,
            aspect_breakdown,
            sentiment_breakdown,
            computed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            _new_id(),
            campaign_id,
            phase,
            metric_date,
            current_nss,
            baseline_nss,
            nss_uplift,
            current_volume,
            baseline_volume,
            volume_lift_pct,
            json.dumps(metrics.get("aspect_breakdown", {}), ensure_ascii=False),
            json.dumps(metrics.get("sentiment_breakdown", {}), ensure_ascii=False),
            computed_at,
        ),
    )


def _signal_id_for_row(row: pd.Series, phase: str) -> str:
    """Construit un identifiant stable de signal pour le lien campagne-signal."""
    signal_id = row.get("signal_id")
    if signal_id not in (None, ""):
        return str(signal_id)

    source_url = row.get("source_url")
    if source_url not in (None, ""):
        return str(source_url)

    timestamp = row.get("timestamp")
    if pd.notna(timestamp):
        return f"{phase}:{row.name}:{pd.Timestamp(timestamp).isoformat()}"
    return f"{phase}:{row.name}"


def _persist_campaign_signal_links(
    connection: sqlite3.Connection,
    campaign_id: str,
    phase: str,
    phase_df: pd.DataFrame,
    campaign: dict,
    computed_at: str,
) -> None:
    """Persiste les signaux attribués à une campagne pour une phase donnée."""
    if phase_df.empty:
        return

    rows = []
    for _, row in phase_df.iterrows():
        rows.append(
            (
                _new_id(),
                campaign_id,
                _signal_id_for_row(row, phase),
                phase,
                compute_attribution_score(row, campaign),
                computed_at,
            )
        )

    connection.executemany(
        """
        INSERT INTO campaign_signal_links (
            link_id,
            campaign_id,
            signal_id,
            phase,
            attribution_score,
            attributed_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        rows,
    )


def _campaign_alert_threshold(
    connection: sqlite3.Connection,
    rule_id: str,
    default: float,
    client_id: str | None = None,
) -> float:
    """Lit un seuil de règle d'alerte en base avec repli sur une valeur par défaut."""
    effective_client_id = (
        str(client_id).strip()
        if isinstance(client_id, str) and str(client_id).strip()
        else config.DEFAULT_CLIENT_ID
    )
    try:
        row = connection.execute(
            """
            SELECT threshold_value
            FROM alert_rules
            WHERE alert_rule_id = ? AND client_id = ?
            """,
            (rule_id, effective_client_id),
        ).fetchone()
    except sqlite3.Error:
        return default

    if row is None or row["threshold_value"] in (None, ""):
        return default
    try:
        return float(row["threshold_value"])
    except (TypeError, ValueError):
        return default


def _maybe_create_campaign_alerts(
    connection: sqlite3.Connection,
    campaign: dict,
    phases: dict[str, dict],
    computed_at: str,
) -> None:
    """Crée les alertes campagne prévues par le PRD si les conditions sont remplies."""
    campaign_id = str(campaign["campaign_id"])
    navigation_url = f"/campaigns?campaign_id={campaign_id}"
    pre_metrics = phases["pre"]
    active_metrics = phases["active"]
    post_metrics = phases["post"]

    pre_nss = pre_metrics.get("nss")
    active_nss = active_metrics.get("nss")
    post_nss = post_metrics.get("nss")
    client_id = campaign.get("client_id")

    positive_threshold = _campaign_alert_threshold(
        connection,
        "campaign_impact_positive",
        10.0,
        client_id=client_id,
    )
    post_uplift = None
    if pre_nss is not None and post_nss is not None:
        post_uplift = round(float(post_nss) - float(pre_nss), 2)

    if post_uplift is not None and post_uplift > positive_threshold:
        create_alert(
            title=f"Impact positif détecté pour {campaign.get('campaign_name')}",
            description=(
                f"La campagne {campaign.get('campaign_name')} montre un uplift NSS de "
                f"{post_uplift:+.1f} points en post-campagne."
            ),
            severity="high" if post_uplift < 30 else "critical",
            dedup_key=f"campaign_impact_positive:{campaign_id}",
            navigation_url=navigation_url,
            alert_payload={
                "rule_id": "campaign_impact_positive",
                "campaign_id": campaign_id,
                "campaign_name": campaign.get("campaign_name"),
                "phase": "post",
                "nss_pre": pre_nss,
                "nss_post": post_nss,
                "uplift_nss": post_uplift,
                "computed_at": computed_at,
            },
            client_id=client_id,
        )

    underperformance_threshold = _campaign_alert_threshold(
        connection,
        "campaign_underperformance",
        0.0,
        client_id=client_id,
    )
    active_uplift = None
    if pre_nss is not None and active_nss is not None:
        active_uplift = round(float(active_nss) - float(pre_nss), 2)

    start_date = campaign.get("start_date")
    active_duration_days = None
    try:
        start_dt = pd.to_datetime(start_date) if start_date else None
    except Exception:
        start_dt = None
    if start_dt is not None:
        if active_metrics.get("volume", 0) > 0:
            active_duration_days = max(
                1,
                (
                    pd.to_datetime(computed_at).normalize() - start_dt.normalize()
                ).days + 1,
            )
        else:
            active_duration_days = max(1, (pd.Timestamp.now().normalize() - start_dt.normalize()).days + 1)

    if (
        campaign.get("status") == "active"
        and active_uplift is not None
        and active_uplift <= underperformance_threshold
        and int(active_metrics.get("volume", 0) or 0) > 50
        and (active_duration_days or 0) > 7
    ):
        create_alert(
            title=f"Sous-performance de campagne: {campaign.get('campaign_name')}",
            description=(
                f"La campagne active {campaign.get('campaign_name')} sous-performe avec un uplift NSS "
                f"de {active_uplift:+.1f} points après plus de 7 jours."
            ),
            severity="critical",
            dedup_key=f"campaign_underperformance:{campaign_id}",
            navigation_url=navigation_url,
            alert_payload={
                "rule_id": "campaign_underperformance",
                "campaign_id": campaign_id,
                "campaign_name": campaign.get("campaign_name"),
                "phase": "active",
                "nss_pre": pre_nss,
                "nss_active": active_nss,
                "uplift_nss": active_uplift,
                "active_duration_days": active_duration_days,
                "computed_at": computed_at,
            },
            client_id=client_id,
        )


# ---------------------------------------------------------------------------
# Calcul d'impact global
# ---------------------------------------------------------------------------


def compute_campaign_impact(
    campaign_id: str,
    df_annotated: pd.DataFrame,
) -> dict:
    """Calcule l'impact d'une campagne sur les métriques NSS (3 fenêtres).

    Returns dict conforme à INTERFACES.md Section 4.1.
    """
    _empty_phase = {"nss": None, "volume": 0, "aspect_breakdown": {}, "sentiment_breakdown": {}}

    campaign = get_campaign(campaign_id)
    if campaign is None:
        logger.warning("Campagne introuvable : %s", campaign_id)
        return {
            "campaign_id": campaign_id,
            "campaign_name": None,
            "phases": {"pre": dict(_empty_phase), "active": dict(_empty_phase), "post": dict(_empty_phase)},
            "uplift_nss": None,
            "uplift_volume_pct": None,
            "is_reliable": False,
            "reliability_note": "Campagne introuvable",
        }

    start_date = campaign.get("start_date")
    end_date = campaign.get("end_date")
    pre_window = int(campaign.get("pre_window_days") or DEFAULT_PRE_WINDOW_DAYS)
    post_window = int(campaign.get("post_window_days") or DEFAULT_POST_WINDOW_DAYS)
    campaign_scope = dict(campaign)
    campaign_scope["keywords"] = []

    # Calcul des bornes temporelles de chaque fenêtre
    if start_date:
        start_dt = pd.to_datetime(start_date)
        pre_start = (start_dt - timedelta(days=pre_window)).strftime("%Y-%m-%d")
        pre_end = (start_dt - timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        pre_start = pre_end = None

    if end_date:
        end_dt = pd.to_datetime(end_date)
        post_start = (end_dt + timedelta(days=1)).strftime("%Y-%m-%d")
        post_end = (end_dt + timedelta(days=post_window)).strftime("%Y-%m-%d")
    else:
        post_start = post_end = None

    # Filtrage par fenêtre
    if df_annotated.empty:
        df_pre = df_active = df_post = pd.DataFrame()
    else:
        df_pre = (
            filter_signals_for_campaign(df_annotated, campaign_scope, pre_start, pre_end)
            if pre_start and pre_end else pd.DataFrame()
        )
        df_active = (
            filter_signals_for_campaign(df_annotated, campaign_scope, start_date, end_date)
            if start_date and end_date else pd.DataFrame()
        )
        df_post = (
            filter_signals_for_campaign(df_annotated, campaign_scope, post_start, post_end)
            if post_start and post_end else pd.DataFrame()
        )

    phases = {
        "pre": _phase_metrics(df_pre),
        "active": _phase_metrics(df_active),
        "post": _phase_metrics(df_post),
    }

    pre_nss = phases["pre"]["nss"]
    post_nss = phases["post"]["nss"]
    pre_vol = phases["pre"]["volume"]
    post_vol = phases["post"]["volume"]

    uplift_nss: float | None = None
    if pre_nss is not None and post_nss is not None:
        uplift_nss = round(post_nss - pre_nss, 2)

    uplift_volume_pct: float | None = None
    if pre_vol > 0:
        uplift_volume_pct = round((post_vol - pre_vol) / pre_vol * 100, 2)

    is_reliable = (
        phases["pre"]["volume"] >= MIN_SIGNALS_FOR_ATTRIBUTION
        and phases["active"]["volume"] >= MIN_SIGNALS_FOR_ATTRIBUTION
        and phases["post"]["volume"] >= MIN_SIGNALS_FOR_ATTRIBUTION
    )
    reliability_note = (
        ""
        if is_reliable
        else f"Volume insuffisant pour une attribution fiable (minimum {MIN_SIGNALS_FOR_ATTRIBUTION} signaux par phase)"
    )

    computed_at = _now()
    metric_date = computed_at[:10]
    with _get_connection() as connection:
        _persist_campaign_snapshot(connection, campaign_id, "pre", phases["pre"], phases["pre"], metric_date, computed_at)
        _persist_campaign_snapshot(connection, campaign_id, "active", phases["active"], phases["pre"], metric_date, computed_at)
        _persist_campaign_snapshot(connection, campaign_id, "post", phases["post"], phases["pre"], metric_date, computed_at)
        _persist_campaign_signal_links(connection, campaign_id, "pre", df_pre, campaign, computed_at)
        _persist_campaign_signal_links(connection, campaign_id, "active", df_active, campaign, computed_at)
        _persist_campaign_signal_links(connection, campaign_id, "post", df_post, campaign, computed_at)
        connection.commit()
        _maybe_create_campaign_alerts(connection, campaign, phases, computed_at)

    return {
        "campaign_id": campaign_id,
        "campaign_name": campaign.get("campaign_name"),
        "phases": phases,
        "uplift_nss": uplift_nss,
        "uplift_volume_pct": uplift_volume_pct,
        "is_reliable": is_reliable,
        "reliability_note": reliability_note,
    }


# ---------------------------------------------------------------------------
# Score d'attribution individuel
# ---------------------------------------------------------------------------


def compute_attribution_score(row: pd.Series, campaign: dict) -> float:
    """Calcule le score d'attribution d'un signal à une campagne (0.0 à 1.0).

    Logique :
    - Base (fenêtre temporelle + plateforme) : 0.3
    - Handle influenceur mentionné dans text : +0.4
    - >= 1 keyword présent dans text : +0.2 (max)
    - aspect correspond à target_aspects : +0.1
    """
    score = 0.3  # Score de base : signal dans la fenêtre temporelle + plateforme

    text = str(row.get("text", "")).lower()

    # Handle influenceur
    handle = campaign.get("influencer_handle")
    if handle and str(handle).lower() in text:
        score += 0.4

    # Keywords
    keywords = campaign.get("keywords") or []
    if keywords and any(str(kw).lower() in text for kw in keywords):
        score += 0.2

    # Aspect
    target_aspects = campaign.get("target_aspects") or []
    row_aspect = row.get("aspect", "")
    if target_aspects and row_aspect in target_aspects:
        score += 0.1

    return min(round(score, 2), 1.0)
