"""Seed data de démonstration pour RamyPulse — Expo 2026.

Peuple la base SQLite avec des données réalistes pour le tenant demo-expo-2026
(marque YaghurtPlus) afin de valider les dashboards lors des démos.

Usage :
    python scripts/seed_demo.py --tenant demo-expo-2026 --reset
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import random
import sqlite3
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Setup path
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from core.database import DatabaseManager

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BRAND = "YaghurtPlus"
PRODUCT = "Yaghourt Abricot 150g"
COMPETITOR = "LactoDar"

# Canaux (standards RamyPulse)
CHANNELS = ["facebook", "google_maps", "youtube"]
CHANNEL_WEIGHTS = [0.40, 0.35, 0.25]

# Sentiments (standards RamyPulse: 5 classes)
SENTIMENT_MAP = {
    "positif": 0.40,
    "neutre": 0.30,
    "négatif": 0.20,
    "très_négatif": 0.10,
}

# Aspects (standards RamyPulse)
ASPECTS = ["goût", "emballage", "prix", "disponibilité", "fraîcheur"]

# Wilayas
WILAYAS = ["Alger", "Oran", "Constantine", "Annaba", "Tlemcen"]

# NSS → health_score formula: health_score = int((nss + 100) / 2)
# health_score = 72  →  nss = 72*2 - 100 = 44
TARGET_NSS = 44.0
TARGET_DELTA_NSS = 5.0

NOW = datetime.now()


# ---------------------------------------------------------------------------
# Verbatim corpus (darija/français réaliste)
# ---------------------------------------------------------------------------
_POSITIVE_VERBATIMS = [
    "Yaghourt abricot vraiment délicieux, texture parfaite !",
    "J'adore ce yaghourt, goût naturel et frais",
    "Meilleur yaghourt du marché algérien, franchement",
    "Prix correct et qualité au rendez-vous, merci YaghurtPlus",
    "زبدة ! هذا الياغورت ماشي بصح، ولا كيف",
    "Waouw quelle fraîcheur, je recommande vivement",
    "Disponible partout à Alger, facile à trouver",
    "L'emballage est pratique et bien scellé",
    "Rani nebgha had lya9hourt, tay3jebni bzzaf",
    "Bon produit, rapport qualité/prix excellent",
    "Texture crémeuse comme j'aime, parfait au petit déjeuner",
    "Mon yaghourt préféré depuis des années",
    "Très bonne fraîcheur, toujours dans les dates",
    "كي نشريه من فرنك دايما يكون طازج",
    "Le goût abricot est authentique, pas artificiel",
    "Idéal pour les enfants, naturel et sain",
    "5 étoiles sans hésiter pour YaghurtPlus",
    "Packaging amélioré récemment, bien mieux",
    "رانا نحوسو على هذ النتاج في كل حتة",
    "Super produit, bravo à l'équipe RamyPulse",
]
_NEUTRAL_VERBATIMS = [
    "Yaghourt correct, ni exceptionnel ni mauvais",
    "Prix habituel, rien de spécial à signaler",
    "Disponible normalement dans les supérettes",
    "Goût standard, correspond à la description",
    "C'est un yaghourt classique, ça fait le travail",
    "هادي منتوج عادي، ما عندوش حاجة مميزة",
    "J'en achète parfois, quand il n'y a pas d'autre choix",
    "Emballage normal, rien de particulier",
    "Fraîcheur acceptable, dans les normes",
    "Prix moyen du marché, pas d'avantage spécifique",
    "OK pour le quotidien, sans plus",
    "Texture normale pour un yaghourt brassé",
    "Je l'achète de temps en temps",
    "Rien à redire, produit standard",
    "Normal comme tous les yaghourts du marché",
]
_NEGATIVE_VERBATIMS = [
    "Le goût a changé dernièrement, moins bon qu'avant",
    "Trop cher par rapport à la concurrence",
    "Rupture de stock trop fréquente chez moi",
    "Emballage qui fuit parfois, problème de qualité",
    "ما عجبنيش كيما قبل، غيروا الطعم",
    "Texture trop liquide, je suis déçu",
    "Difficile à trouver dans ma région",
    "Le prix a augmenté mais la qualité non",
    "Pas frais à l'achat, date limite trop proche",
    "Emballage peu pratique, difficile à ouvrir",
    "Goût artificiel, pas naturel du tout",
    "Service client inexistant quand j'ai eu un problème",
    "Parfois des lots défectueux, attention",
    "Distribution inégale selon les wilayas",
    "Moins bon que LactoDar, désolé",
]
_VERY_NEGATIVE_VERBATIMS = [
    "Produit périmé vendu, inadmissible !",
    "Fermentation suspecte dans mon yaghourt, danger",
    "لقيت ياغورت مبدل في عبوة يبانها كلشي صحيح",
    "Très mauvaise expérience, yaghourt avarié",
    "Je ne rachèterai plus jamais ce produit",
    "Problème de contamination signalé, à éviter",
    "Packaging défectueux, produit exposé à l'air",
    "Goût acide et mauvais, j'ai été malade",
    "Prix scandaleux pour une qualité déplorable",
    "Alerte qualité sur ce lot, méfiez-vous",
]


def _pick_verbatim(sentiment: str) -> str:
    pools = {
        "positif": _POSITIVE_VERBATIMS,
        "très_positif": _POSITIVE_VERBATIMS,
        "neutre": _NEUTRAL_VERBATIMS,
        "négatif": _NEGATIVE_VERBATIMS,
        "très_négatif": _VERY_NEGATIVE_VERBATIMS,
    }
    pool = pools.get(sentiment, _NEUTRAL_VERBATIMS)
    return random.choice(pool) + f" (#{random.randint(1000, 9999)})"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _now_iso(offset_days: int = 0) -> str:
    return (NOW + timedelta(days=offset_days)).isoformat()


def _uid() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Reset
# ---------------------------------------------------------------------------
def reset_tenant(conn: sqlite3.Connection, client_id: str) -> None:
    logger.info("Suppression des données du tenant %s …", client_id)
    tables_with_client = [
        "enriched_signals",
        "normalized_records",
        "raw_documents",
        "watchlist_metric_snapshots",
        "watch_runs",
        "watch_run_steps",
        "alerts",
        "recommendations",
        "campaigns",
        "watchlists",
        "sources",
        "api_keys",
        "clients",
        "client_agent_config",
    ]
    for table in tables_with_client:
        try:
            conn.execute(f"DELETE FROM {table} WHERE client_id = ?", (client_id,))
        except sqlite3.OperationalError:
            pass  # Table might not have client_id column
    # watchlist_metric_snapshots references watchlist_id not client_id
    conn.execute(
        """DELETE FROM watchlist_metric_snapshots
           WHERE watchlist_id IN (
               SELECT watchlist_id FROM watchlists WHERE client_id = ?
           )""",
        (client_id,),
    )
    conn.commit()
    logger.info("Reset terminé.")


# ---------------------------------------------------------------------------
# Seeding functions
# ---------------------------------------------------------------------------
def seed_client(conn: sqlite3.Connection, client_id: str) -> None:
    conn.execute(
        """INSERT OR REPLACE INTO clients (client_id, client_name, industry, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?)""",
        (client_id, "YaghurtPlus Algeria", "agroalimentaire", _now_iso(-90), _now_iso()),
    )
    logger.info("Client %s créé.", client_id)


def seed_api_key(conn: sqlite3.Connection, client_id: str, raw_key: str = "dev") -> None:
    key_id = f"key-seed-demo-{client_id[:8]}"
    conn.execute(
        """INSERT OR REPLACE INTO api_keys
           (key_id, client_id, key_hash, key_prefix, label, scopes, is_active, created_at, last_used_at)
           VALUES (?, ?, ?, ?, ?, ?, 1, ?, NULL)""",
        (
            key_id,
            client_id,
            _hash_key(raw_key),
            raw_key[:12],
            "demo-seed",
            '["*"]',
            _now_iso(),
        ),
    )
    logger.info("API key '%s' enregistrée pour %s.", raw_key, client_id)


def seed_source(conn: sqlite3.Connection, client_id: str) -> str:
    source_id = f"src-demo-{client_id[:8]}"
    conn.execute(
        """INSERT OR REPLACE INTO sources
           (source_id, client_id, source_name, platform, source_type,
            owner_type, auth_mode, is_active, source_purpose, source_priority,
            created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, 1, ?, ?)""",
        (
            source_id,
            client_id,
            "Demo Seed Source",
            "multi",
            "scraped",
            "brand",
            "none",
            "brand_monitoring",
            _now_iso(-90),
            _now_iso(),
        ),
    )
    return source_id


def seed_verbatims(
    conn: sqlite3.Connection, client_id: str, source_id: str, count: int = 200
) -> list[str]:
    """Crée normalized_records + enriched_signals."""
    # Build sentiment distribution
    sentiments: list[str] = []
    for label, pct in SENTIMENT_MAP.items():
        sentiments += [label] * int(count * pct)
    # Fill remaining to reach exactly `count`
    while len(sentiments) < count:
        sentiments.append("positif")
    random.shuffle(sentiments)

    # Build channel distribution
    channels = random.choices(CHANNELS, weights=CHANNEL_WEIGHTS, k=count)

    signal_ids = []
    for i in range(count):
        days_ago = random.randint(0, 60)
        ts = _now_iso(-days_ago)
        wilaya = random.choice(WILAYAS)
        aspect = random.choice(ASPECTS)
        sentiment = sentiments[i]
        channel = channels[i]
        url = f"https://{channel}.com/yaghurtplus/{uuid.uuid4().hex[:8]}"

        # normalized_record
        nr_id = _uid()
        text = _pick_verbatim(sentiment)
        conn.execute(
            """INSERT INTO normalized_records
               (normalized_record_id, client_id, source_id, text, text_original,
                channel, source_url, published_at, language, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (nr_id, client_id, source_id, text, text, channel, url, ts, "fr-ar", _now_iso()),
        )

        # enriched_signal
        sig_id = _uid()
        conn.execute(
            """INSERT INTO enriched_signals
               (signal_id, client_id, normalized_record_id, source_id,
                sentiment_label, confidence, aspect, aspects, brand, product,
                wilaya, source_url, channel, event_timestamp, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                sig_id,
                client_id,
                nr_id,
                source_id,
                sentiment,
                round(random.uniform(0.72, 0.98), 3),
                aspect,
                json.dumps([aspect]),
                BRAND,
                PRODUCT,
                wilaya,
                url,
                channel,
                ts,
                _now_iso(),
            ),
        )
        signal_ids.append(sig_id)

    logger.info("%d verbatims (normalized_records + enriched_signals) insérés.", count)
    return signal_ids


def seed_watchlists(conn: sqlite3.Connection, client_id: str) -> tuple[str, str]:
    """Crée 2 watchlists : marque et concurrent."""
    wl_brand_id = f"wl-brand-{client_id[:8]}"
    wl_comp_id = f"wl-comp-{client_id[:8]}"
    ts = _now_iso()

    conn.execute(
        """INSERT OR REPLACE INTO watchlists
           (watchlist_id, client_id, watchlist_name, description, scope_type,
            filters, is_active, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)""",
        (
            wl_brand_id,
            client_id,
            f"Veille {BRAND}",
            f"Surveillance marque {BRAND} — toutes sources",
            "brand",
            json.dumps({"brand": BRAND, "channels": CHANNELS}),
            ts,
            ts,
        ),
    )

    conn.execute(
        """INSERT OR REPLACE INTO watchlists
           (watchlist_id, client_id, watchlist_name, description, scope_type,
            filters, is_active, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)""",
        (
            wl_comp_id,
            client_id,
            f"Veille concurrent {COMPETITOR}",
            f"Surveillance concurrent {COMPETITOR}",
            "competitor",
            json.dumps({"brand": COMPETITOR, "channels": CHANNELS}),
            ts,
            ts,
        ),
    )

    logger.info("2 watchlists créées (brand + concurrent).")
    return wl_brand_id, wl_comp_id


def seed_metric_snapshots(
    conn: sqlite3.Connection, wl_brand_id: str, wl_comp_id: str
) -> None:
    """Injecte le snapshot de métriques pour health_score=72 (NSS=44, delta=+5)."""
    snap_id = f"snap-{_uid()[:12]}"
    conn.execute(
        """INSERT INTO watchlist_metric_snapshots
           (snapshot_id, watchlist_id, nss_current, nss_previous,
            volume_current, volume_previous, delta_nss, delta_volume_pct,
            aspect_breakdown, computed_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            snap_id,
            wl_brand_id,
            TARGET_NSS,           # nss_current=44 → health_score=72
            TARGET_NSS - TARGET_DELTA_NSS,  # nss_previous=39
            200,
            185,
            TARGET_DELTA_NSS,     # delta_nss=+5
            8.1,
            json.dumps({"goût": 38, "emballage": 22, "prix": 17, "disponibilité": 14, "fraîcheur": 9}),
            _now_iso(),
        ),
    )
    # Snapshot pour le concurrent (NSS neutre)
    snap_comp_id = f"snap-{_uid()[:12]}"
    conn.execute(
        """INSERT INTO watchlist_metric_snapshots
           (snapshot_id, watchlist_id, nss_current, nss_previous,
            volume_current, volume_previous, delta_nss, delta_volume_pct,
            aspect_breakdown, computed_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            snap_comp_id,
            wl_comp_id,
            10.0,
            12.0,
            95,
            88,
            -2.0,
            7.9,
            json.dumps({"goût": 30, "emballage": 20, "prix": 25, "disponibilité": 15, "fraîcheur": 10}),
            _now_iso(),
        ),
    )
    logger.info(
        "Snapshots métriques insérés. NSS brand=%.1f → health_score=%d, delta=+%.1f",
        TARGET_NSS,
        int((TARGET_NSS + 100) / 2),
        TARGET_DELTA_NSS,
    )


def seed_alerts(conn: sqlite3.Connection, client_id: str, wl_brand_id: str) -> None:
    """Crée 2 critiques, 3 moyennes, 5 basses."""
    alert_specs = [
        ("critical", "Chute critique du NSS — aspect goût", "Le NSS sur l'aspect goût a chuté de 12 pts en 72h. Signaux négatifs Facebook en hausse."),
        ("critical", "Volume de mentions négatives en explosion", "Surge de 45% de mentions très_négatif sur Google Maps — 3 wilayas concernées."),
        ("medium", "Disponibilité dégradée — Oran", "Rupture de stock signalée dans 4 points de vente Oran sur les 48 dernières heures."),
        ("medium", "Pression concurrentielle LactoDar", f"{COMPETITOR} gagne 8 pts NSS en 2 semaines, risque de captation de marché."),
        ("medium", "Emballage — réclamations en hausse", "15 verbatims négatifs sur l'emballage cette semaine, vs 3 la semaine précédente."),
        ("low", "Alerte saisonnière prix", "Comparaison prix YaghurtPlus vs marché : écart +7% détecté sur Constantine."),
        ("low", "Fraîcheur — signaux YouTube", "3 vidéos YouTube mentionnent des problèmes de date limite sur le lot ALG-2026-04."),
        ("low", "Baisse légère engagement Facebook", "Le taux d'engagement des posts Facebook a baissé de 3% cette semaine."),
        ("low", "Alerte volume faible — Annaba", "Volume de mentions Annaba inférieur au seuil minimal. Couverture à renforcer."),
        ("low", "Rapport hebdomadaire disponible", "Le rapport NSS de la semaine 15/2026 est prêt à consulter."),
    ]

    for severity, title, description in alert_specs:
        alert_id = f"alrt-{_uid()[:12]}"
        conn.execute(
            """INSERT INTO alerts
               (alert_id, client_id, watchlist_id, title, description,
                severity, status, detected_at, alert_payload, navigation_url)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                alert_id,
                client_id,
                wl_brand_id,
                title,
                description,
                severity,
                "new",
                _now_iso(-random.randint(0, 7)),
                json.dumps({"brand": BRAND, "auto_generated": True}),
                f"/dashboard?alert={alert_id}",
            ),
        )

    logger.info("10 alertes insérées (2 critiques, 3 moyennes, 5 basses).")


def seed_recommendations(conn: sqlite3.Connection, client_id: str) -> None:
    """Crée 3 recommandations IA pré-générées."""
    reco_data = [
        {
            "title": "Renforcer la distribution en wilaya d'Oran",
            "priority": "haute",
            "platform": "distribution",
            "rationale": "Les ruptures fréquentes à Oran génèrent des verbatims négatifs sur disponibilité. Corriger ce point améliorerait le NSS de 3–5 pts.",
            "kpi": "NSS disponibilité +5 pts, réduction verbatims négatifs Oran -30%",
            "action": "Engager négociation avec 3 distributeurs supplémentaires dans la wilaya d'Oran d'ici J+15.",
        },
        {
            "title": "Campagne de réassurance qualité sur Facebook",
            "priority": "haute",
            "platform": "facebook",
            "rationale": "Surge de contenus négatifs sur l'aspect goût. Une campagne UGC montrant le processus qualité peut inverser la tendance.",
            "kpi": "NSS goût +4 pts, reach estimé 120K utilisateurs",
            "action": "Lancer 3 posts vidéo de type 'behind the scenes' en semaine 17/2026, avec influenceur tier micro.",
        },
        {
            "title": "Ajuster le positionnement prix face à LactoDar",
            "priority": "moyenne",
            "platform": "multi",
            "rationale": f"L'écart de prix avec {COMPETITOR} crée une friction. Offre promotionnelle ciblée ou pack famille peut contenir la pression.",
            "kpi": f"Part de voix vs {COMPETITOR} +5%, NPS prix +8 pts",
            "action": "Tester une offre duo (-10%) sur les 3 grandes surfaces Alger en mai 2026.",
        },
    ]

    for i, reco in enumerate(reco_data):
        rec_id = f"rec-seed-{client_id[:6]}-{i:02d}"
        recommendations_json = json.dumps([
            {
                "action": reco["action"],
                "platform": reco["platform"],
                "priority": reco["priority"],
                "rationale": reco["rationale"],
                "expected_kpi": reco["kpi"],
                "title": reco["title"],
            }
        ])
        conn.execute(
            """INSERT OR REPLACE INTO recommendations
               (recommendation_id, client_id, trigger_type, analysis_summary,
                recommendations, confidence_score, provider_used, model_used,
                status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                rec_id,
                client_id,
                "manual",
                f"Analyse basée sur {200} signaux — période 60 jours. NSS brand={TARGET_NSS:.0f}, delta=+{TARGET_DELTA_NSS:.0f} pts.",
                recommendations_json,
                round(0.78 + i * 0.04, 2),
                "demo_seed",
                "gpt-4o",
                "active",
                _now_iso(-i * 3),
            ),
        )

    logger.info("3 recommandations IA insérées.")


def seed_campaigns(conn: sqlite3.Connection, client_id: str) -> None:
    """Crée 3 campagnes : 1 active, 1 archivée, 1 terminée."""
    campaigns = [
        {
            "campaign_id": f"cmp-active-{client_id[:8]}",
            "campaign_name": "Ramadan Digital 2026 — YaghurtPlus",
            "campaign_type": "influencer",
            "platform": "facebook",
            "description": "Campagne influenceurs Ramadan ciblant les wilayas Alger & Oran.",
            "influencer_handle": "@yaghourt_life_dz",
            "influencer_tier": "micro",
            "target_segment": "familles 25-45 ans",
            "target_aspects": json.dumps(["goût", "disponibilité"]),
            "target_regions": json.dumps(["Alger", "Oran"]),
            "keywords": json.dumps(["ramadan", "yaghourt", "sehour"]),
            "budget_dza": 450000,
            "start_date": _now_iso(-15)[:10],
            "end_date": _now_iso(15)[:10],
            "status": "active",
        },
        {
            "campaign_id": f"cmp-done-{client_id[:8]}",
            "campaign_name": "Lancement Printemps 2026",
            "campaign_type": "paid_social",
            "platform": "facebook",
            "description": "Campagne paid Facebook pour le lancement du Yaghourt Abricot 150g.",
            "influencer_handle": None,
            "influencer_tier": None,
            "target_segment": "jeunes adultes 18-35",
            "target_aspects": json.dumps(["goût", "emballage"]),
            "target_regions": json.dumps(["Alger", "Constantine", "Annaba"]),
            "keywords": json.dumps(["nouveau", "yaghourt", "abricot"]),
            "budget_dza": 300000,
            "start_date": _now_iso(-45)[:10],
            "end_date": _now_iso(-16)[:10],
            "status": "completed",
        },
        {
            "campaign_id": f"cmp-arch-{client_id[:8]}",
            "campaign_name": "Test Micro-Influenceurs Q4 2025",
            "campaign_type": "influencer",
            "platform": "youtube",
            "description": "Campagne test YouTube avec micro-influenceurs food.",
            "influencer_handle": "@food_dz_vlogs",
            "influencer_tier": "micro",
            "target_segment": "foodies 20-40",
            "target_aspects": json.dumps(["goût", "fraîcheur"]),
            "target_regions": json.dumps(["Alger", "Tlemcen"]),
            "keywords": json.dumps(["review", "yaghourt", "test"]),
            "budget_dza": 120000,
            "start_date": _now_iso(-120)[:10],
            "end_date": _now_iso(-91)[:10],
            "status": "cancelled",
        },
    ]

    for c in campaigns:
        conn.execute(
            """INSERT OR REPLACE INTO campaigns
               (campaign_id, client_id, campaign_name, campaign_type, platform,
                description, influencer_handle, influencer_tier, target_segment,
                target_aspects, target_regions, keywords, budget_dza,
                start_date, end_date, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                c["campaign_id"], client_id, c["campaign_name"], c["campaign_type"],
                c["platform"], c["description"], c.get("influencer_handle"),
                c.get("influencer_tier"), c["target_segment"], c["target_aspects"],
                c["target_regions"], c["keywords"], c["budget_dza"],
                c["start_date"], c["end_date"], c["status"],
                _now_iso(-90), _now_iso(),
            ),
        )

    logger.info("3 campagnes insérées (1 active, 1 terminée, 1 archivée).")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description="Seed demo data pour RamyPulse Expo")
    parser.add_argument("--tenant", default="demo-expo-2026", help="client_id cible")
    parser.add_argument("--reset", action="store_true", help="Efface les données existantes")
    parser.add_argument("--api-key", default="dev", help="Clé API à enregistrer (défaut: dev)")
    parser.add_argument("--verbatims", type=int, default=200, help="Nombre de verbatims (défaut: 200)")
    args = parser.parse_args()

    client_id = args.tenant
    logger.info("=== Seed demo RamyPulse — tenant: %s ===", client_id)

    # S'assurer que les tables existent
    db = DatabaseManager()
    db.create_tables()

    conn = sqlite3.connect(str(config.SQLITE_DB_PATH))
    conn.row_factory = sqlite3.Row

    try:
        if args.reset:
            reset_tenant(conn, client_id)

        seed_client(conn, client_id)
        seed_api_key(conn, client_id, args.api_key)
        source_id = seed_source(conn, client_id)
        seed_verbatims(conn, client_id, source_id, args.verbatims)
        wl_brand_id, wl_comp_id = seed_watchlists(conn, client_id)
        seed_metric_snapshots(conn, wl_brand_id, wl_comp_id)
        seed_alerts(conn, client_id, wl_brand_id)
        seed_recommendations(conn, client_id)
        seed_campaigns(conn, client_id)

        conn.commit()

        logger.info("")
        logger.info("✅ Seed terminé avec succès !")
        logger.info("   Tenant        : %s", client_id)
        logger.info("   API Key        : %s  (header: X-API-Key: %s)", args.api_key, args.api_key)
        logger.info("   Health score   : %d/100 (NSS=%.0f, delta=+%.0f)", int((TARGET_NSS + 100) / 2), TARGET_NSS, TARGET_DELTA_NSS)
        logger.info("   Verbatims      : %d", args.verbatims)
        logger.info("   DB             : %s", config.SQLITE_DB_PATH)
        logger.info("")
        logger.info("Test rapide :")
        logger.info("  curl http://localhost:8000/api/health")
        logger.info("  curl -H 'X-API-Key: %s' 'http://localhost:8000/api/dashboard/summary?client_id=%s'", args.api_key, client_id)

    except Exception:
        conn.rollback()
        logger.exception("Erreur lors du seed, rollback effectué.")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
