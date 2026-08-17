"""Crée un client de démonstration V3 depuis le corpus DEV annoté V0.4.

Le script ne modifie que le tenant demandé dans la base locale. Les textes,
langues, aspects, alertes et preuves viennent du corpus d'entraînement ; seuls les
horodatages de démonstration et les objets produit (veille, campagne, actions) sont
générés pour rendre tous les écrans navigables.

Usage :
    python scripts/seed_training_demo.py --reset
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote_plus

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import config
from core.database import DatabaseManager

logger = logging.getLogger(__name__)

DEFAULT_TENANT = "demo-expo-2026"
DEFAULT_API_KEY = "dev"
ANCHOR = datetime(2026, 8, 17, 12, 0, tzinfo=timezone.utc)
PLATFORM_HOME = {
    "facebook": "https://www.facebook.com/",
    "google_maps": "https://www.google.com/maps",
    "youtube": "https://www.youtube.com/",
}


def _find_corpus(explicit: str | None) -> Path:
    candidates = []
    if explicit:
        candidates.append(Path(explicit))
    candidates.extend(
        [
            config.PROCESSED_DATA_DIR / "slm_v2_sft" / "master_dev.jsonl",
            PROJECT_ROOT.parent
            / "ramypulse"
            / "data"
            / "processed"
            / "slm_v2_sft"
            / "master_dev.jsonl",
        ]
    )
    for candidate in candidates:
        resolved = candidate.expanduser().resolve()
        if resolved.exists():
            return resolved
    raise FileNotFoundError("master_dev.jsonl introuvable ; utilisez --corpus")


def _hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def _legacy_sentiment(annotation: dict) -> str:
    sentiment = annotation.get("sentiment") or {}
    label = str(sentiment.get("label") or "neutre")
    intensity = str(sentiment.get("intensity") or "faible")
    if label == "positif" and intensity == "forte":
        return "très_positif"
    if label == "negatif" and intensity == "forte":
        return "très_négatif"
    if label == "negatif":
        return "négatif"
    if label == "mixte":
        return "neutre"
    return label


def _channel(context: dict) -> str:
    source = str(context.get("source") or "").strip()
    return "google_maps" if source == "google_maps" else "facebook"


def _source_url(context: dict, channel: str) -> str:
    brand = str(context.get("brand") or "").strip()
    city = str(context.get("city") or "").strip()
    query = " ".join(value for value in (brand, city) if value).strip()
    if channel == "google_maps" and query:
        return f"https://www.google.com/maps/search/?api=1&query={quote_plus(query)}"
    if channel == "facebook" and query:
        return f"https://www.facebook.com/search/top?q={quote_plus(query)}"
    return PLATFORM_HOME[channel]


def _demo_timestamp(index: int) -> str:
    return (ANCHOR - timedelta(days=index % 90, minutes=(index * 17) % 1440)).isoformat()


def _reset_tenant(connection: sqlite3.Connection, client_id: str) -> None:
    connection.execute(
        "DELETE FROM campaign_signal_links WHERE campaign_id IN "
        "(SELECT campaign_id FROM campaigns WHERE client_id = ?)",
        (client_id,),
    )
    connection.execute(
        "DELETE FROM campaign_metrics_snapshots WHERE campaign_id IN "
        "(SELECT campaign_id FROM campaigns WHERE client_id = ?)",
        (client_id,),
    )
    connection.execute(
        "DELETE FROM watchlist_metric_snapshots WHERE watchlist_id IN "
        "(SELECT watchlist_id FROM watchlists WHERE client_id = ?)",
        (client_id,),
    )
    connection.execute(
        "DELETE FROM watch_run_steps WHERE run_id IN "
        "(SELECT run_id FROM watch_runs WHERE client_id = ?)",
        (client_id,),
    )
    for table in (
        "enriched_signals",
        "normalized_records",
        "raw_documents",
        "watch_runs",
        "alerts",
        "recommendations",
        "campaigns",
        "watchlists",
        "sources",
        "api_keys",
        "client_agent_config",
        "notifications",
        "clients",
    ):
        connection.execute(f"DELETE FROM {table} WHERE client_id = ?", (client_id,))


def _seed_identity(connection: sqlite3.Connection, client_id: str, raw_key: str) -> None:
    now = ANCHOR.isoformat()
    connection.execute(
        """
        INSERT INTO clients (client_id, client_name, industry, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (client_id, "LIDAL Pulse — Démonstration métier", "multi-sectoriel", now, now),
    )
    connection.execute(
        """
        INSERT INTO api_keys (
            key_id, client_id, key_hash, key_prefix, label, scopes,
            is_active, created_at, last_used_at
        ) VALUES (?, ?, ?, ?, ?, ?, 1, ?, NULL)
        """,
        (
            f"key-training-demo-{client_id}",
            client_id,
            _hash_key(raw_key),
            raw_key[:12],
            "training-corpus-demo",
            '["*"]',
            now,
        ),
    )


def _seed_sources(connection: sqlite3.Connection, client_id: str) -> dict[str, str]:
    now = ANCHOR.isoformat()
    source_ids = {
        "google_maps": f"src-training-maps-{client_id}",
        "facebook": f"src-training-public-{client_id}",
    }
    for channel, source_id in source_ids.items():
        label = "Google Maps — corpus annoté" if channel == "google_maps" else "Corpus public algérien annoté"
        connection.execute(
            """
            INSERT INTO sources (
                source_id, client_id, source_name, platform, source_type,
                owner_type, auth_mode, config_json, is_active,
                source_purpose, source_priority, coverage_key,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?)
            """,
            (
                source_id,
                client_id,
                label,
                channel,
                "training_corpus",
                "public",
                "none",
                json.dumps({"demo_only": True, "schema_version": "0.4.0"}),
                "brand_monitoring",
                1,
                f"training:{channel}:v0.4",
                now,
                now,
            ),
        )
    return source_ids


def _seed_records(
    connection: sqlite3.Connection,
    *,
    corpus_path: Path,
    client_id: str,
    source_ids: dict[str, str],
) -> dict[str, Counter]:
    counters = {
        "sentiments": Counter(),
        "aspects": Counter(),
        "negative_aspects": Counter(),
        "alerts": Counter(),
        "languages": Counter(),
        "channels": Counter(),
    }
    for index, line in enumerate(corpus_path.open(encoding="utf-8")):
        row = json.loads(line)
        text = str(row.get("text") or "").strip()
        annotation = row.get("annotation") or {}
        context = row.get("context") or {}
        example_id = str(row.get("example_id") or f"row-{index}")
        channel = _channel(context)
        source_id = source_ids[channel]
        timestamp = _demo_timestamp(index)
        source_url = _source_url(context, channel)
        language = str((annotation.get("language") or {}).get("dominant") or "autre")
        scripts = list((annotation.get("language") or {}).get("scripts") or [])
        aspects = list(annotation.get("aspects") or [])
        aspect_families = list(dict.fromkeys(str(item.get("family")) for item in aspects if item.get("family")))
        first_aspect = aspect_families[0] if aspect_families else None
        sentiment = _legacy_sentiment(annotation)
        validation = row.get("validation") or {}
        confidence = 0.98 if validation.get("annotation_schema_valid") and validation.get("all_evidence_exact") else 0.85
        raw_id = f"raw-training-{example_id}"
        normalized_id = f"norm-training-{example_id}"
        signal_id = f"sig-training-{example_id}"
        raw_metadata = {
            "channel": channel,
            "source_url": source_url,
            "published_at": timestamp,
            "watchlist_id": f"wl-training-all-{client_id}",
            "training_demo": True,
            "source_provenance": row.get("source_provenance") or {},
            "monitoring_target": annotation.get("monitoring_target"),
            "topic": context.get("topic"),
        }
        connection.execute(
            """
            INSERT INTO raw_documents (
                raw_document_id, client_id, source_id, external_document_id,
                raw_payload, raw_text, raw_metadata, checksum_sha256,
                platform, canonical_url, canonical_key, collected_at,
                is_normalized, normalizer_version, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
            """,
            (
                raw_id,
                client_id,
                source_id,
                example_id,
                json.dumps({"context": context, "validation": validation}, ensure_ascii=False),
                text,
                json.dumps(raw_metadata, ensure_ascii=False),
                hashlib.sha256(text.encode("utf-8")).hexdigest(),
                channel,
                source_url,
                f"training:{example_id}",
                timestamp,
                "training-demo-v0.4",
                timestamp,
            ),
        )
        connection.execute(
            """
            INSERT INTO normalized_records (
                normalized_record_id, client_id, source_id, raw_document_id,
                text, text_original, channel, source_url, published_at,
                language, script_detected, normalized_payload, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                normalized_id,
                client_id,
                source_id,
                raw_id,
                text,
                text,
                channel,
                source_url,
                timestamp,
                language,
                "/".join(scripts),
                json.dumps({"training_demo": True}, ensure_ascii=False),
                timestamp,
            ),
        )
        connection.execute(
            """
            INSERT INTO enriched_signals (
                signal_id, client_id, normalized_record_id, source_id,
                sentiment_label, confidence, aspect, aspects, aspect_sentiments,
                brand, product, wilaya, source_url, channel, event_timestamp,
                normalizer_version, annotation_json, raw_model_output,
                validation_status, model_version, compiler_version, inference_ms,
                annotation_created_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                signal_id,
                client_id,
                normalized_id,
                source_id,
                sentiment,
                confidence,
                first_aspect,
                json.dumps(aspect_families, ensure_ascii=False),
                json.dumps(aspects, ensure_ascii=False),
                context.get("brand") or "Corpus public DZ",
                context.get("topic") or "Avis multisectoriel",
                context.get("city"),
                source_url,
                channel,
                timestamp,
                "training-demo-v0.4",
                json.dumps(annotation, ensure_ascii=False),
                row.get("compact_trace"),
                "valid" if validation.get("annotation_schema_valid") else "dataset_warning",
                "teacher-gold-v0.4",
                "dataset-import-v1",
                0,
                timestamp,
                timestamp,
            ),
        )
        counters["sentiments"][sentiment] += 1
        counters["aspects"].update(aspect_families)
        counters["languages"][language] += 1
        counters["channels"][channel] += 1
        counters["alerts"].update(str(item.get("type")) for item in annotation.get("alerts") or [] if item.get("type"))
        counters["negative_aspects"].update(
            str(item.get("family")) for item in aspects if item.get("sentiment") == "negatif" and item.get("family")
        )
    return counters


def _nss(sentiments: Counter) -> float:
    total = sum(sentiments.values())
    positive = sentiments["positif"] + sentiments["très_positif"]
    negative = sentiments["négatif"] + sentiments["très_négatif"]
    return round(((positive - negative) / total) * 100, 1) if total else 0.0


def _seed_product_surfaces(
    connection: sqlite3.Connection,
    *,
    client_id: str,
    counters: dict[str, Counter],
) -> None:
    now = ANCHOR.isoformat()
    total = sum(counters["sentiments"].values())
    nss = _nss(counters["sentiments"])
    watchlist_id = f"wl-training-all-{client_id}"
    connection.execute(
        """
        INSERT INTO watchlists (
            watchlist_id, client_id, watchlist_name, description,
            scope_type, filters, is_active, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
        """,
        (
            watchlist_id,
            client_id,
            "Voix client multisectorielle — Algérie",
            "Corpus DEV V0.4 : avis français, arabe, darija et arabizi",
            "sector",
            json.dumps(
                {
                    "brand_name": "LIDAL Demo",
                    "keywords": ["service", "qualité", "prix", "disponibilité"],
                    "channels": sorted(counters["channels"]),
                    "languages": sorted(counters["languages"]),
                },
                ensure_ascii=False,
            ),
            now,
            now,
        ),
    )
    connection.execute(
        """
        INSERT INTO watchlist_metric_snapshots (
            snapshot_id, watchlist_id, nss_current, nss_previous,
            volume_current, volume_previous, delta_nss, delta_volume_pct,
            aspect_breakdown, computed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            f"snap-training-{client_id}",
            watchlist_id,
            nss,
            nss - 4.2,
            total,
            max(total - 54, 1),
            4.2,
            round((54 / max(total - 54, 1)) * 100, 1),
            json.dumps(dict(counters["aspects"].most_common(10)), ensure_ascii=False),
            now,
        ),
    )

    alert_labels = {
        "qualite_produit": "Signal qualité produit",
        "rupture_service": "Rupture ou indisponibilité de service",
        "securite_sante": "Risque sécurité ou santé",
        "fraude_arnaque": "Suspicion de fraude ou d’arnaque",
        "juridique_conformite": "Signal juridique ou conformité",
        "rupture_stock": "Rupture de stock",
        "harcelement_discrimination": "Harcèlement ou discrimination",
        "reputation_virale": "Risque réputationnel viral",
    }
    top_alerts = counters["alerts"].most_common(5)
    for index, (alert_type, count) in enumerate(top_alerts):
        severity = "critical" if index < 2 else "medium"
        connection.execute(
            """
            INSERT INTO alerts (
                alert_id, client_id, watchlist_id, alert_rule_id, title,
                description, severity, status, detected_at, alert_payload,
                dedup_key, navigation_url
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'new', ?, ?, ?, ?)
            """,
            (
                f"alert-training-{index}-{client_id}",
                client_id,
                watchlist_id,
                alert_type,
                alert_labels.get(alert_type, alert_type.replace("_", " ").title()),
                f"{count} commentaire(s) annoté(s) portent ce signal dans le corpus de démonstration.",
                severity,
                _demo_timestamp(index),
                json.dumps({"count": count, "source": "training_corpus_v0.4"}),
                f"training:{alert_type}",
                "/alertes",
            ),
        )

    for index, (family, count) in enumerate(counters["negative_aspects"].most_common(3)):
        readable = family.replace("_", " ")
        recommendation = {
            "title": f"Prioriser l’analyse : {readable}",
            "description": f"{count} signaux négatifs concernent cette famille. Examiner les preuves et segmenter par secteur avant toute action.",
            "priority": "high" if index == 0 else "medium",
            "target_platform": "Toutes les sources",
            "expected_kpi": "Réduction des signaux négatifs sur la prochaine période",
        }
        connection.execute(
            """
            INSERT INTO recommendations (
                recommendation_id, client_id, trigger_type, trigger_id,
                analysis_summary, recommendations, confidence_score,
                data_quality_note, provider_used, model_used, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?)
            """,
            (
                f"rec-training-{index}-{client_id}",
                client_id,
                "annotation_v0.4",
                family,
                f"Analyse de {total} commentaires annotés — {readable}",
                json.dumps([recommendation], ensure_ascii=False),
                0.92,
                "Recommandation de démonstration calculée à partir du corpus DEV annoté.",
                "deterministic_demo",
                "teacher-gold-v0.4",
                now,
            ),
        )

    campaigns = [
        (
            "camp-training-active",
            "Écoute client — qualité de service",
            "monitoring",
            "multi_platform",
            "Campagne de démonstration pour suivre les signaux de qualité de service.",
            "active",
            180000,
        ),
        (
            "camp-training-completed",
            "Réassurance confiance et réputation",
            "awareness",
            "facebook",
            "Scénario de démonstration basé sur les aspects confiance et réputation.",
            "completed",
            120000,
        ),
    ]
    for index, (campaign_id, name, kind, platform, description, status, budget) in enumerate(campaigns):
        connection.execute(
            """
            INSERT INTO campaigns (
                campaign_id, client_id, campaign_name, campaign_type, platform,
                description, target_segment, target_aspects, target_regions,
                keywords, budget_dza, start_date, end_date, status,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"{campaign_id}-{client_id}",
                client_id,
                name,
                kind,
                platform,
                description,
                "Clients et usagers en Algérie",
                json.dumps([item[0] for item in counters["aspects"].most_common(3)], ensure_ascii=False),
                json.dumps(["Alger", "Oran", "Constantine"], ensure_ascii=False),
                json.dumps(["service", "qualité", "confiance"], ensure_ascii=False),
                budget,
                (ANCHOR - timedelta(days=30 + index * 30)).date().isoformat(),
                (ANCHOR + timedelta(days=30 - index * 15)).date().isoformat(),
                status,
                now,
                now,
            ),
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed V3 depuis master_dev V0.4")
    parser.add_argument("--tenant", default=DEFAULT_TENANT)
    parser.add_argument("--api-key", default=DEFAULT_API_KEY)
    parser.add_argument("--corpus")
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()

    corpus_path = _find_corpus(args.corpus)
    database = DatabaseManager()
    database.create_tables()
    connection = sqlite3.connect(str(config.SQLITE_DB_PATH))
    try:
        if args.reset:
            _reset_tenant(connection, args.tenant)
        _seed_identity(connection, args.tenant, args.api_key)
        sources = _seed_sources(connection, args.tenant)
        counters = _seed_records(
            connection,
            corpus_path=corpus_path,
            client_id=args.tenant,
            source_ids=sources,
        )
        _seed_product_surfaces(connection, client_id=args.tenant, counters=counters)
        connection.commit()
    except Exception:
        connection.rollback()
        logger.exception("Échec du seed corpus ; rollback complet")
        return 1
    finally:
        connection.close()
        database.close()

    summary = {
        "tenant": args.tenant,
        "corpus": str(corpus_path),
        "comments": sum(counters["sentiments"].values()),
        "nss": _nss(counters["sentiments"]),
        "sentiments": dict(counters["sentiments"]),
        "languages": dict(counters["languages"]),
        "channels": dict(counters["channels"]),
        "top_aspects": dict(counters["aspects"].most_common(8)),
        "alerts": dict(counters["alerts"]),
        "database": str(config.SQLITE_DB_PATH),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
