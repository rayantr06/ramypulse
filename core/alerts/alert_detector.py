"""Moteur de detection des alertes RamyPulse."""

from __future__ import annotations

import json
import logging
import sqlite3
import unicodedata
import uuid
from datetime import datetime
from urllib.parse import urlencode

import pandas as pd

import config
from core.alerts.alert_manager import create_alert
from core.analysis.nss_calculator import calculate_nss
from core.watchlists.watchlist_manager import list_watchlists

logger = logging.getLogger(__name__)

_DDL_WATCHLIST_METRIC_SNAPSHOTS = """
CREATE TABLE IF NOT EXISTS watchlist_metric_snapshots (
    snapshot_id        TEXT PRIMARY KEY,
    watchlist_id       TEXT NOT NULL,
    nss_current        REAL,
    nss_previous       REAL,
    volume_current     INTEGER DEFAULT 0,
    volume_previous    INTEGER DEFAULT 0,
    delta_nss          REAL,
    delta_volume_pct   REAL,
    aspect_breakdown   TEXT DEFAULT '{}',
    computed_at        TEXT NOT NULL
)
"""

_SENTIMENT_ALIASES = {
    "tres_positif": "très_positif",
    "positif": "positif",
    "neutre": "neutre",
    "negatif": "négatif",
    "tres_negatif": "très_négatif",
}
_ASPECT_ALIASES = {
    "gout": "goût",
    "emballage": "emballage",
    "prix": "prix",
    "disponibilite": "disponibilité",
    "fraicheur": "fraîcheur",
}


def _slug(value: object) -> str:
    """Normalise une valeur en slug minuscule et sans accent."""
    if value is None:
        return ""
    text = str(value).strip().lower()
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def _canonical_sentiment(value: object) -> str:
    """Mappe un libelle de sentiment vers le jeu canonique RamyPulse."""
    slug = _slug(value)
    return _SENTIMENT_ALIASES.get(slug, str(value).strip() if value is not None else "")


def _canonical_aspect(value: object) -> str:
    """Mappe un aspect vers le libelle canonique RamyPulse."""
    slug = _slug(value)
    return _ASPECT_ALIASES.get(slug, str(value).strip() if value is not None else "")


def _prepare_dataframe(df_annotated: pd.DataFrame) -> pd.DataFrame:
    """Normalise les colonnes minimales attendues par le moteur d'alertes."""
    dataframe = df_annotated.copy()
    for column in (
        "text",
        "text_original",
        "sentiment_label",
        "channel",
        "aspect",
        "source_url",
        "wilaya",
        "product",
    ):
        if column not in dataframe.columns:
            dataframe[column] = ""

    dataframe["timestamp"] = pd.to_datetime(dataframe.get("timestamp"), errors="coerce")
    dataframe["text"] = dataframe["text"].fillna("").astype(str)
    dataframe["channel"] = dataframe["channel"].fillna("").astype(str).str.strip().str.lower()
    dataframe["aspect"] = dataframe["aspect"].apply(_canonical_aspect)
    dataframe["wilaya"] = dataframe["wilaya"].fillna("").astype(str).str.strip().str.lower()
    dataframe["product"] = dataframe["product"].fillna("").astype(str).str.strip().str.lower()
    dataframe["sentiment_label"] = dataframe["sentiment_label"].apply(_canonical_sentiment)
    dataframe["source_url"] = dataframe["source_url"].fillna("").astype(str)
    return dataframe


def _reference_time(dataframe: pd.DataFrame) -> pd.Timestamp:
    """Determine le point temporel de reference du cycle courant."""
    valid = dataframe["timestamp"].dropna()
    if valid.empty:
        return pd.Timestamp.now().floor("min")
    return valid.max()


def _filter_scope(watchlist: dict, dataframe: pd.DataFrame) -> pd.DataFrame:
    """Applique le perimetre de watchlist au DataFrame partage."""
    filters = watchlist.get("filters", {})
    scoped = dataframe.copy()
    mapping = {
        "channel": "channel",
        "aspect": "aspect",
        "wilaya": "wilaya",
        "product": "product",
        "sentiment": "sentiment_label",
    }
    for filter_key, column in mapping.items():
        value = filters.get(filter_key)
        if value in (None, ""):
            continue
        slug_value = _slug(value)
        scoped = scoped[scoped[column].map(_slug) == slug_value]
    return scoped


def _split_periods(
    scoped: pd.DataFrame,
    reference_time: pd.Timestamp,
    period_days: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Decoupe les jeux de donnees en fenetre courante et precedente."""
    current_start = reference_time - pd.Timedelta(days=period_days)
    previous_start = current_start - pd.Timedelta(days=period_days)
    current = scoped[(scoped["timestamp"] > current_start) & (scoped["timestamp"] <= reference_time)]
    previous = scoped[(scoped["timestamp"] > previous_start) & (scoped["timestamp"] <= current_start)]
    return current, previous


def _nss_or_none(dataframe: pd.DataFrame, metrics: dict[str, object]) -> float | None:
    """Retourne le NSS si des lignes existent, sinon None."""
    if dataframe.empty:
        return None
    return float(metrics["nss_global"])


def _volume_delta_pct(current_volume: int, previous_volume: int) -> float | None:
    """Calcule le delta de volume en pourcentage."""
    if previous_volume <= 0:
        return None
    return ((current_volume - previous_volume) / previous_volume) * 100.0


def _iso_week_label(reference_time: pd.Timestamp) -> str:
    """Construit un libelle ISO de semaine pour la deduplication."""
    iso = reference_time.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def _build_navigation_url(filters: dict) -> str:
    """Construit un lien direct vers l'explorer a partir des filtres."""
    query = {
        key: value
        for key, value in filters.items()
        if value not in (None, "", [], {})
        and key in {"channel", "aspect", "wilaya", "product", "sentiment"}
    }
    suffix = f"?{urlencode(query)}" if query else ""
    return f"/explorer{suffix}"


def _compute_negative_ratio(current_metrics: dict[str, object], current_volume: int) -> float:
    """Calcule la part des signaux negatifs dans le volume courant."""
    if current_volume <= 0:
        return 0.0
    distribution = current_metrics["distribution"]
    negative_count = distribution.get("négatif", 0) + distribution.get("très_négatif", 0)
    return (negative_count / current_volume) * 100.0


def _severity(rule_id: str, *, value: float | None = None, ratio: float | None = None) -> str:
    """Attribue une severite simple par type de regle et amplitude."""
    if rule_id == "nss_critical_low":
        return "critical" if value is not None and value < 0 else "high"
    if rule_id == "negative_volume_surge":
        return "critical" if ratio is not None and ratio >= 80 else "high"
    if rule_id == "volume_anomaly":
        return "critical" if ratio is not None and ratio >= 3.0 else "high"
    if rule_id == "nss_temporal_drift":
        return "high" if value is not None and value <= -20 else "medium"
    if rule_id.startswith("segment_divergence_"):
        return "critical" if value is not None and value >= 50 else "high"
    if rule_id == "no_recent_signals":
        return "high"
    if rule_id.startswith("aspect_critical_"):
        return "critical" if value is not None and value <= -40 else "high"
    if rule_id == "volume_drop":
        return "high" if value is not None and value <= -75 else "medium"
    return "medium"


def _get_connection() -> sqlite3.Connection:
    """Ouvre une connexion SQLite pour les règles et snapshots d'alertes."""
    connection = sqlite3.connect(config.SQLITE_DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute(_DDL_WATCHLIST_METRIC_SNAPSHOTS)
    connection.commit()
    return connection


def _new_id() -> str:
    """Génère un identifiant UUID textuel."""
    return str(uuid.uuid4())


def _now() -> str:
    """Retourne un timestamp ISO courant."""
    return datetime.now().isoformat()


def _rule_key(rule_id: str) -> str:
    """Ramène un identifiant de règle dérivé vers sa règle de base."""
    if rule_id.startswith("aspect_critical_"):
        return "aspect_critical"
    if rule_id.startswith("segment_divergence_"):
        return "segment_divergence"
    return rule_id


def _load_rule_settings(
    connection: sqlite3.Connection,
    client_id: str | None,
) -> dict[str, dict]:
    """Charge les paramètres de règles seedés en base avec repli silencieux."""
    effective_client_id = (
        str(client_id).strip()
        if isinstance(client_id, str) and str(client_id).strip()
        else config.DEFAULT_CLIENT_ID
    )
    try:
        rows = connection.execute(
            """
            SELECT alert_rule_id, threshold_value, lookback_window, severity_level, comparator
            FROM alert_rules
            WHERE client_id = ?
              AND is_active = 1
            """,
            (effective_client_id,),
        ).fetchall()
    except sqlite3.Error:
        return {}

    settings: dict[str, dict] = {}
    for row in rows:
        settings[str(row["alert_rule_id"])] = {
            "threshold_value": row["threshold_value"],
            "lookback_window": row["lookback_window"],
            "severity_level": row["severity_level"],
            "comparator": row["comparator"],
        }
    return settings


def _rule_threshold(rule_settings: dict[str, dict], rule_id: str, default: float) -> float:
    """Retourne le seuil configuré pour une règle avec valeur de repli."""
    payload = rule_settings.get(_rule_key(rule_id), {})
    value = payload.get("threshold_value")
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _rule_lookback_days(rule_settings: dict[str, dict], rule_id: str, default: int) -> int:
    """Extrait un lookback en jours depuis le format seedé `7d`."""
    payload = rule_settings.get(_rule_key(rule_id), {})
    raw = str(payload.get("lookback_window") or "").strip().lower()
    if raw.endswith("d"):
        raw = raw[:-1]
    try:
        return max(1, int(raw))
    except (TypeError, ValueError):
        return default


def _persist_watchlist_snapshot(connection: sqlite3.Connection, metrics: dict) -> None:
    """Persiste un snapshot des métriques calculées pour une watchlist."""
    connection.execute(
        """
        INSERT INTO watchlist_metric_snapshots (
            snapshot_id,
            watchlist_id,
            nss_current,
            nss_previous,
            volume_current,
            volume_previous,
            delta_nss,
            delta_volume_pct,
            aspect_breakdown,
            computed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            _new_id(),
            metrics["watchlist_id"],
            metrics.get("nss_current"),
            metrics.get("nss_previous"),
            int(metrics.get("volume_current", 0) or 0),
            int(metrics.get("volume_previous", 0) or 0),
            metrics.get("delta_nss"),
            metrics.get("delta_volume_pct"),
            json.dumps(metrics.get("aspect_breakdown", {}), ensure_ascii=False),
            metrics.get("computed_at") or _now(),
        ),
    )


def _load_recent_watchlist_snapshots(
    connection: sqlite3.Connection,
    watchlist_id: str,
    limit: int,
) -> list[dict]:
    """Charge les snapshots precedents d'une watchlist pour les regles historiques."""
    rows = connection.execute(
        """
        SELECT watchlist_id, nss_current, volume_current, computed_at
        FROM watchlist_metric_snapshots
        WHERE watchlist_id = ?
        ORDER BY computed_at DESC
        LIMIT ?
        """,
        (watchlist_id, limit),
    ).fetchall()
    history: list[dict] = []
    for row in rows:
        payload = dict(row)
        payload["computed_at"] = pd.to_datetime(payload.get("computed_at"), errors="coerce")
        history.append(payload)
    return list(reversed(history))


def _z_score(current_value: float, history_values: list[float]) -> float | None:
    """Calcule un z-score simple contre un historique numerique."""
    if len(history_values) < 2:
        return None
    series = pd.Series(history_values, dtype="float64")
    std = float(series.std(ddof=0))
    if std <= 0:
        return None
    return (current_value - float(series.mean())) / std


def _series_is_strictly_decreasing(values: list[float]) -> bool:
    """Indique si une serie baisse strictement a chaque periode."""
    if len(values) < 2:
        return False
    return all(values[index] < values[index - 1] for index in range(1, len(values)))


def _segment_nss_map(current: pd.DataFrame, column: str) -> dict[str, float]:
    """Calcule le NSS par segment pour la fenetre courante."""
    if column not in current.columns:
        return {}
    mapping: dict[str, float] = {}
    for segment_value, group in current.groupby(column):
        if segment_value in (None, ""):
            continue
        metrics = calculate_nss(group)
        mapping[str(segment_value)] = float(metrics["nss_global"])
    return mapping


def _meets_min_volume(watchlist: dict, metrics: dict, *, include_previous: bool = False) -> bool:
    """Indique si le volume observé est suffisant pour les règles métriques."""
    min_volume = int(watchlist.get("filters", {}).get("min_volume", 0) or 0)
    if min_volume <= 0:
        return True
    current_volume = int(metrics.get("volume_current", 0) or 0)
    if include_previous:
        previous_volume = int(metrics.get("volume_previous", 0) or 0)
        return current_volume >= min_volume and previous_volume >= min_volume
    return current_volume >= min_volume


def _deserialize_list(value: str | None) -> list[str]:
    """Deserialise une liste JSON de campagne."""
    if not value:
        return []
    try:
        payload = json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return []
    if not isinstance(payload, list):
        return []
    return [str(item) for item in payload if item not in (None, "")]


def _campaign_columns(connection: sqlite3.Connection) -> set[str]:
    """Retourne les colonnes disponibles pour la table campaigns."""
    rows = connection.execute("PRAGMA table_info(campaigns)").fetchall()
    return {row["name"] for row in rows}


def _matching_campaigns(watchlist: dict, reference_time: pd.Timestamp) -> list[dict]:
    """Retourne les campagnes actives compatibles avec la watchlist si disponibles."""
    wl_client_id = watchlist.get("client_id")
    if not isinstance(wl_client_id, str) or not str(wl_client_id).strip():
        return []
    effective_client_id = str(wl_client_id).strip()
    try:
        connection = sqlite3.connect(config.SQLITE_DB_PATH)
        connection.row_factory = sqlite3.Row
        columns = _campaign_columns(connection)
        expected = {
            "campaign_id",
            "client_id",
            "campaign_name",
            "platform",
            "target_aspects",
            "target_regions",
            "start_date",
            "end_date",
            "status",
        }
        if not expected.issubset(columns):
            return []

        rows = connection.execute(
            """
            SELECT campaign_id, campaign_name, platform, target_aspects, target_regions,
                   start_date, end_date, status
            FROM campaigns
            WHERE client_id = ?
              AND status = 'active'
            """,
            (effective_client_id,),
        ).fetchall()
    except sqlite3.Error:
        logger.debug("Table campaigns indisponible pour enrichissement des alertes", exc_info=True)
        return []

    current_date = reference_time.date().isoformat()
    filters = watchlist.get("filters", {})
    channel_slug = _slug(filters.get("channel"))
    aspect_slug = _slug(filters.get("aspect"))
    wilaya_slug = _slug(filters.get("wilaya"))

    matches: list[dict] = []
    try:
        for row in rows:
            if row["start_date"] and row["start_date"] > current_date:
                continue
            if row["end_date"] and row["end_date"] < current_date:
                continue

            platform_slug = _slug(row["platform"])
            if channel_slug and platform_slug not in {"", "multi_platform", channel_slug}:
                continue

            campaign_aspects = _deserialize_list(row["target_aspects"])
            if aspect_slug and campaign_aspects and aspect_slug not in {_slug(item) for item in campaign_aspects}:
                continue

            campaign_regions = _deserialize_list(row["target_regions"])
            if wilaya_slug and campaign_regions and wilaya_slug not in {_slug(item) for item in campaign_regions}:
                continue

            current_uplift = None
            try:
                snapshot = connection.execute(
                    """
                    SELECT nss_uplift
                    FROM campaign_metrics_snapshots
                    WHERE campaign_id = ?
                    ORDER BY computed_at DESC, metric_date DESC
                    LIMIT 1
                    """,
                    (row["campaign_id"],),
                ).fetchone()
                if snapshot is not None and snapshot["nss_uplift"] is not None:
                    current_uplift = float(snapshot["nss_uplift"])
            except sqlite3.Error:
                current_uplift = None

            matches.append(
                {
                    "campaign_id": row["campaign_id"],
                    "campaign_name": row["campaign_name"],
                    "phase": "active",
                    "current_uplift": current_uplift,
                }
            )
    finally:
        try:
            connection.close()
        except Exception:  # pragma: no cover - fermeture defensive
            pass
    return matches


def _base_payload(
    watchlist: dict,
    rule_id: str,
    metrics: dict,
    *,
    metric_current: float | int | None = None,
    metric_previous: float | int | None = None,
    extra: dict | None = None,
) -> dict:
    """Assemble le payload standard partage par toutes les alertes v1."""
    payload = {
        "rule_id": rule_id,
        "watchlist_id": watchlist["watchlist_id"],
        "watchlist_name": watchlist["watchlist_name"],
        "scope": watchlist.get("filters", {}),
        "metric_current": metric_current,
        "metric_previous": metric_previous,
        "delta": metrics.get("delta_nss"),
        "delta_pct": metrics.get("delta_volume_pct"),
        "period": _iso_week_label(pd.Timestamp(metrics["computed_at"])),
        "aspect_breakdown": metrics.get("aspect_breakdown", {}),
    }
    if extra:
        payload.update(extra)
    return payload


def _create_detection_alert(
    watchlist: dict,
    rule_id: str,
    title: str,
    description: str,
    metrics: dict,
    *,
    metric_current: float | int | None = None,
    metric_previous: float | int | None = None,
    extra: dict | None = None,
    severity_value: float | None = None,
    severity_ratio: float | None = None,
) -> str | None:
    """Cree une alerte issue du moteur de detection avec deduplication uniforme."""
    reference_time = pd.to_datetime(metrics["computed_at"], errors="coerce")
    if pd.isna(reference_time):
        reference_time = pd.Timestamp.now().floor("min")

    payload = _base_payload(
        watchlist,
        rule_id,
        metrics,
        metric_current=metric_current,
        metric_previous=metric_previous,
        extra=extra,
    )
    active_campaigns = _matching_campaigns(watchlist, reference_time)
    if active_campaigns:
        payload["active_campaigns"] = active_campaigns
        payload["context"] = "Cette derive survient pendant une campagne active sur le meme perimetre."

    dedup_key = f"{watchlist['watchlist_id']}:{rule_id}:{_iso_week_label(reference_time)}"
    return create_alert(
        title=title,
        description=description,
        severity=_severity(rule_id, value=severity_value, ratio=severity_ratio),
        alert_payload=payload,
        watchlist_id=watchlist["watchlist_id"],
        dedup_key=dedup_key,
        navigation_url=_build_navigation_url(watchlist.get("filters", {})),
        client_id=watchlist.get("client_id"),
    )


def compute_watchlist_metrics(
    watchlist: dict,
    df_annotated: pd.DataFrame,
) -> dict:
    """Calcule les metriques courantes et precedentes d'une watchlist."""
    dataframe = _prepare_dataframe(df_annotated)
    scoped = _filter_scope(watchlist, dataframe)
    reference_time = _reference_time(dataframe)
    period_days = int(watchlist.get("filters", {}).get("period_days", 7) or 7)
    current, previous = _split_periods(scoped, reference_time, period_days)
    current_metrics = calculate_nss(current)
    previous_metrics = calculate_nss(previous)
    nss_current = _nss_or_none(current, current_metrics)
    nss_previous = _nss_or_none(previous, previous_metrics)
    volume_current = int(len(current))
    volume_previous = int(len(previous))

    return {
        "watchlist_id": watchlist["watchlist_id"],
        "nss_current": nss_current,
        "nss_previous": nss_previous,
        "volume_current": volume_current,
        "volume_previous": volume_previous,
        "delta_nss": (
            nss_current - nss_previous
            if nss_current is not None and nss_previous is not None
            else None
        ),
        "delta_volume_pct": _volume_delta_pct(volume_current, volume_previous),
        "aspect_breakdown": dict(current_metrics["nss_by_aspect"]),
        "computed_at": reference_time.isoformat(),
    }


def run_alert_detection(df_annotated: pd.DataFrame) -> list[str]:
    """Evalue toutes les watchlists actives et cree les alertes detectees."""
    dataframe = _prepare_dataframe(df_annotated)
    reference_time = _reference_time(dataframe)
    created_alert_ids: list[str] = []
    rule_settings_cache: dict[str, dict[str, dict]] = {}

    for watchlist in list_watchlists():
        client_id = (
            str(watchlist.get("client_id")).strip()
            if isinstance(watchlist.get("client_id"), str) and str(watchlist.get("client_id")).strip()
            else config.DEFAULT_CLIENT_ID
        )
        if client_id not in rule_settings_cache:
            with _get_connection() as connection:
                rule_settings_cache[client_id] = _load_rule_settings(connection, client_id)
        rule_settings = rule_settings_cache[client_id]
        scoped = _filter_scope(watchlist, dataframe)
        metrics = compute_watchlist_metrics(watchlist, dataframe)
        with _get_connection() as connection:
            history_snapshots = _load_recent_watchlist_snapshots(
                connection,
                watchlist["watchlist_id"],
                limit=12,
            )
            _persist_watchlist_snapshot(connection, metrics)
            connection.commit()

        period_days = int(watchlist.get("filters", {}).get("period_days", 7) or 7)
        current, previous = _split_periods(scoped, reference_time, period_days)
        current_nss_metrics = calculate_nss(current)
        current_nss = metrics["nss_current"]
        negative_ratio = _compute_negative_ratio(current_nss_metrics, metrics["volume_current"])
        min_volume_ready = _meets_min_volume(watchlist, metrics)
        volume_rule_ready = _meets_min_volume(watchlist, metrics, include_previous=True)
        nss_threshold = _rule_threshold(rule_settings, "nss_critical_low", 20.0)
        negative_ratio_threshold = _rule_threshold(rule_settings, "negative_volume_surge", 60.0)
        no_recent_days = _rule_lookback_days(rule_settings, "no_recent_signals", 7)
        aspect_threshold = _rule_threshold(rule_settings, "aspect_critical", -10.0)
        volume_drop_threshold = _rule_threshold(rule_settings, "volume_drop", 50.0)
        anomaly_threshold = _rule_threshold(rule_settings, "volume_anomaly", 2.0)
        drift_periods = _rule_lookback_days(rule_settings, "nss_temporal_drift", 3)
        divergence_threshold = _rule_threshold(rule_settings, "segment_divergence", 25.0)

        if min_volume_ready and current_nss is not None and current_nss < nss_threshold:
            alert_id = _create_detection_alert(
                watchlist,
                "nss_critical_low",
                title=f"NSS critique sur {watchlist['watchlist_name']}",
                description=(
                    f"Le NSS courant est a {current_nss:.1f}, sous le seuil de {nss_threshold:.1f} "
                    f"sur la watchlist {watchlist['watchlist_name']}."
                ),
                metrics=metrics,
                metric_current=current_nss,
                metric_previous=metrics["nss_previous"],
                severity_value=current_nss,
            )
            if alert_id:
                created_alert_ids.append(alert_id)

        if min_volume_ready and metrics["volume_current"] > 0 and negative_ratio > negative_ratio_threshold:
            alert_id = _create_detection_alert(
                watchlist,
                "negative_volume_surge",
                title=f"Pic de volume negatif sur {watchlist['watchlist_name']}",
                description=(
                    f"{negative_ratio:.1f}% des signaux courants sont negatifs ou tres negatifs "
                    f"sur {watchlist['watchlist_name']}."
                ),
                metrics=metrics,
                metric_current=negative_ratio,
                metric_previous=metrics["volume_previous"],
                extra={"negative_ratio": negative_ratio},
                severity_ratio=negative_ratio,
            )
            if alert_id:
                created_alert_ids.append(alert_id)

        if min_volume_ready:
            historical_volumes = [
                float(item["volume_current"])
                for item in history_snapshots
                if item.get("volume_current") is not None
            ]
            volume_z_score = _z_score(float(metrics["volume_current"]), historical_volumes)
            if volume_z_score is not None and abs(volume_z_score) > anomaly_threshold:
                historical_mean = float(pd.Series(historical_volumes, dtype="float64").mean())
                historical_std = float(pd.Series(historical_volumes, dtype="float64").std(ddof=0))
                alert_id = _create_detection_alert(
                    watchlist,
                    "volume_anomaly",
                    title=f"Anomalie de volume sur {watchlist['watchlist_name']}",
                    description=(
                        f"Le volume courant ({metrics['volume_current']}) s'ecarte fortement de la moyenne "
                        f"historique ({historical_mean:.1f}) sur {watchlist['watchlist_name']}."
                    ),
                    metrics=metrics,
                    metric_current=metrics["volume_current"],
                    metric_previous=historical_mean,
                    extra={
                        "z_score": round(volume_z_score, 2),
                        "historical_mean": round(historical_mean, 2),
                        "historical_std": round(historical_std, 2),
                    },
                    severity_ratio=abs(volume_z_score),
                )
                if alert_id:
                    created_alert_ids.append(alert_id)

        last_signal_at = scoped["timestamp"].dropna().max() if not scoped.empty else pd.NaT
        if pd.isna(last_signal_at) or last_signal_at <= reference_time - pd.Timedelta(days=no_recent_days):
            alert_id = _create_detection_alert(
                watchlist,
                "no_recent_signals",
                title=f"Aucun signal recent pour {watchlist['watchlist_name']}",
                description=(
                    f"Aucun signal n'a ete detecte sur les {no_recent_days} derniers jours pour "
                    f"{watchlist['watchlist_name']}."
                ),
                metrics=metrics,
                metric_current=0,
                metric_previous=metrics["volume_previous"],
                extra={
                    "last_signal_at": (
                        last_signal_at.isoformat() if not pd.isna(last_signal_at) else None
                    )
                },
            )
            if alert_id:
                created_alert_ids.append(alert_id)

        if min_volume_ready:
            for aspect_name, aspect_nss in metrics["aspect_breakdown"].items():
                if aspect_nss >= aspect_threshold:
                    continue
                aspect_slug = _slug(aspect_name)
                alert_id = _create_detection_alert(
                    watchlist,
                    f"aspect_critical_{aspect_slug}",
                    title=f"Aspect critique {aspect_name} sur {watchlist['watchlist_name']}",
                    description=(
                        f"L'aspect {aspect_name} presente un NSS de {aspect_nss:.1f} sur "
                        f"{watchlist['watchlist_name']}."
                    ),
                    metrics=metrics,
                    metric_current=aspect_nss,
                    metric_previous=metrics["nss_previous"],
                    extra={"aspect": aspect_name},
                    severity_value=aspect_nss,
                )
                if alert_id:
                    created_alert_ids.append(alert_id)

            historical_nss = [
                float(item["nss_current"])
                for item in history_snapshots
                if item.get("nss_current") is not None
            ]
            drift_series = historical_nss[-drift_periods:] + ([float(current_nss)] if current_nss is not None else [])
            if len(drift_series) >= drift_periods + 1 and _series_is_strictly_decreasing(drift_series):
                alert_id = _create_detection_alert(
                    watchlist,
                    "nss_temporal_drift",
                    title=f"Derive NSS sur {watchlist['watchlist_name']}",
                    description=(
                        f"Le NSS baisse de facon continue depuis {len(drift_series)} periodes "
                        f"sur {watchlist['watchlist_name']}."
                    ),
                    metrics=metrics,
                    metric_current=current_nss,
                    metric_previous=drift_series[-2] if len(drift_series) >= 2 else None,
                    extra={"nss_series": [round(value, 2) for value in drift_series]},
                    severity_value=current_nss,
                )
                if alert_id:
                    created_alert_ids.append(alert_id)

            segment_candidates: list[tuple[str, dict[str, float]]] = []
            filters = watchlist.get("filters", {})
            if filters.get("wilaya") in (None, ""):
                wilaya_scores = _segment_nss_map(current, "wilaya")
                if len(wilaya_scores) >= 2:
                    segment_candidates.append(("wilaya", wilaya_scores))
            if filters.get("channel") in (None, ""):
                channel_scores = _segment_nss_map(current, "channel")
                if len(channel_scores) >= 2:
                    segment_candidates.append(("channel", channel_scores))

            for segment_name, segment_scores in segment_candidates:
                max_segment = max(segment_scores.items(), key=lambda item: item[1])
                min_segment = min(segment_scores.items(), key=lambda item: item[1])
                gap = abs(max_segment[1] - min_segment[1])
                if gap <= divergence_threshold:
                    continue
                alert_id = _create_detection_alert(
                    watchlist,
                    f"segment_divergence_{segment_name}",
                    title=f"Divergence {segment_name} sur {watchlist['watchlist_name']}",
                    description=(
                        f"L'ecart NSS entre {segment_name} {max_segment[0]} et {min_segment[0]} "
                        f"atteint {gap:.1f} points sur {watchlist['watchlist_name']}."
                    ),
                    metrics=metrics,
                    metric_current=gap,
                    metric_previous=None,
                    extra={
                        "segment": segment_name,
                        "segment_scores": {key: round(value, 2) for key, value in segment_scores.items()},
                        "max_segment": max_segment[0],
                        "min_segment": min_segment[0],
                    },
                    severity_value=gap,
                )
                if alert_id:
                    created_alert_ids.append(alert_id)

        if (
            volume_rule_ready
            and metrics["volume_previous"] > 0
            and metrics["volume_current"] < (metrics["volume_previous"] * (volume_drop_threshold / 100.0))
        ):
            delta_volume_pct = metrics["delta_volume_pct"] or 0.0
            alert_id = _create_detection_alert(
                watchlist,
                "volume_drop",
                title=f"Chute de volume sur {watchlist['watchlist_name']}",
                description=(
                    f"Le volume courant ({metrics['volume_current']}) est inferieur a "
                    f"{volume_drop_threshold:.0f}% du volume de la periode precedente "
                    f"({metrics['volume_previous']})."
                ),
                metrics=metrics,
                metric_current=metrics["volume_current"],
                metric_previous=metrics["volume_previous"],
                extra={"delta_volume_pct": delta_volume_pct},
                severity_value=delta_volume_pct,
            )
            if alert_id:
                created_alert_ids.append(alert_id)

        logger.info(
            "Cycle alertes watchlist=%s created=%s",
            watchlist["watchlist_id"],
            len(created_alert_ids),
        )

    return created_alert_ids
