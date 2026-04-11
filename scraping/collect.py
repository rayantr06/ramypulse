#!/usr/bin/env python3
"""
RamyPulse — Collecteur de commentaires Facebook & Instagram
============================================================

Script autonome qui utilise l'API Apify pour récupérer les commentaires
des pages Facebook et Instagram de Ramy et de ses concurrents.

Usage :
    # Collecter les commentaires de toutes les marques
    python collect.py

    # Collecter une seule marque
    python collect.py --brand "Ramy"

    # Collecter uniquement Facebook ou Instagram
    python collect.py --platform facebook
    python collect.py --platform instagram

    # Mode dry-run (affiche ce qui serait collecté sans lancer Apify)
    python collect.py --dry-run

Prérequis :
    pip install -r requirements.txt
    Créer un fichier .env avec : APIFY_API_TOKEN=apify_api_xxxxx
    (Compte gratuit sur https://apify.com — 10 000 commentaires/mois offerts)
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
load_dotenv(SCRIPT_DIR / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-7s │ %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("ramypulse.collect")

# Actors Apify utilisés
APIFY_FB_COMMENTS = "apify/facebook-comments-scraper"
APIFY_FB_POSTS = "apify/facebook-posts-scraper"
APIFY_IG_COMMENTS = "apify/instagram-comment-scraper"
APIFY_IG_POSTS = "apify/instagram-post-scraper"


# ---------------------------------------------------------------------------
# Chargement de la config
# ---------------------------------------------------------------------------

def load_config(path: Path | None = None) -> dict:
    """Charge targets.yaml et retourne le dictionnaire de configuration."""
    config_path = path or (SCRIPT_DIR / "targets.yaml")
    if not config_path.exists():
        log.error("Fichier de configuration introuvable : %s", config_path)
        sys.exit(1)
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_apify_client():
    """Initialise et retourne le client Apify."""
    try:
        from apify_client import ApifyClient
    except ImportError:
        log.error(
            "apify-client n'est pas installé.\n"
            "  → pip install apify-client"
        )
        sys.exit(1)

    token = os.getenv("APIFY_API_TOKEN")
    if not token:
        log.error(
            "Variable APIFY_API_TOKEN manquante.\n"
            "  → Créer un fichier .env avec : APIFY_API_TOKEN=apify_api_xxxxx\n"
            "  → Obtenir un token gratuit sur https://console.apify.com/account/integrations"
        )
        sys.exit(1)

    return ApifyClient(token)


# ---------------------------------------------------------------------------
# Collecte Facebook
# ---------------------------------------------------------------------------

def discover_facebook_posts(client, page_url: str, max_posts: int) -> list[str]:
    """Récupère les URLs des derniers posts d'une page Facebook via Apify."""
    log.info("  Découverte des posts de %s (max %d)...", page_url, max_posts)

    run_input = {
        "startUrls": [{"url": page_url}],
        "resultsLimit": max_posts,
    }

    try:
        run = client.actor(APIFY_FB_POSTS).call(
            run_input=run_input,
            timeout_secs=300,
        )
    except Exception as e:
        log.warning("  Erreur découverte posts FB : %s", e)
        return []

    post_urls = []
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        url = item.get("postUrl") or item.get("url")
        if url:
            post_urls.append(url)

    log.info("  → %d posts découverts", len(post_urls))
    return post_urls


def collect_facebook_comments(
    client,
    post_urls: list[str],
    brand_name: str,
    cfg: dict,
) -> list[dict]:
    """Collecte les commentaires d'une liste de posts Facebook."""
    if not post_urls:
        return []

    max_comments = cfg.get("max_comments_per_post", 500)
    include_replies = cfg.get("include_replies", True)
    sort_order = cfg.get("sort_order", "RANKED_UNFILTERED")
    newer_than = cfg.get("comments_newer_than")
    delay = cfg.get("delay_between_calls", 2)
    max_retries = cfg.get("max_retries", 3)

    all_comments = []

    for i, url in enumerate(post_urls, 1):
        log.info("  [%d/%d] Collecte FB : %s", i, len(post_urls), url[:80])

        run_input: dict[str, Any] = {
            "startUrls": [{"url": url}],
            "resultsLimit": max_comments,
            "includeNestedComments": include_replies,
            "viewOption": sort_order,
        }
        if newer_than:
            run_input["onlyCommentsNewerThan"] = newer_than

        for attempt in range(1, max_retries + 1):
            try:
                run = client.actor(APIFY_FB_COMMENTS).call(
                    run_input=run_input,
                    timeout_secs=300,
                )
                break
            except Exception as e:
                log.warning("    Tentative %d/%d échouée : %s", attempt, max_retries, e)
                if attempt == max_retries:
                    log.error("    Abandon pour ce post après %d tentatives.", max_retries)
                    continue
                time.sleep(delay * attempt)

        try:
            for item in client.dataset(run["defaultDatasetId"]).iterate_items():
                text = (item.get("text") or "").strip()
                if not text:
                    continue

                comment = {
                    "text": text,
                    "brand": brand_name,
                    "platform": "facebook",
                    "date": item.get("date", ""),
                    "likes": item.get("likesCount", 0),
                    "replies_count": item.get("commentsCount", 0),
                    "author": item.get("profileName", ""),
                    "comment_url": item.get("commentUrl", ""),
                    "post_url": url,
                    "is_reply": bool(item.get("replyToCommentId")),
                    "collected_at": datetime.now(timezone.utc).isoformat(),
                }
                all_comments.append(comment)

                # Récupérer aussi les réponses imbriquées
                for reply in item.get("comments", []):
                    reply_text = (reply.get("text") or "").strip()
                    if not reply_text:
                        continue
                    all_comments.append({
                        "text": reply_text,
                        "brand": brand_name,
                        "platform": "facebook",
                        "date": reply.get("date", ""),
                        "likes": reply.get("likesCount", 0),
                        "replies_count": 0,
                        "author": reply.get("profileName", ""),
                        "comment_url": reply.get("commentUrl", ""),
                        "post_url": url,
                        "is_reply": True,
                        "collected_at": datetime.now(timezone.utc).isoformat(),
                    })
        except Exception as e:
            log.warning("    Erreur lecture résultats : %s", e)

        if i < len(post_urls):
            time.sleep(delay)

    log.info("  → %d commentaires Facebook collectés pour %s", len(all_comments), brand_name)
    return all_comments


# ---------------------------------------------------------------------------
# Collecte Instagram
# ---------------------------------------------------------------------------

def discover_instagram_posts(client, profile_url: str, max_posts: int) -> list[str]:
    """Récupère les URLs des derniers posts d'un profil Instagram via Apify."""
    log.info("  Découverte des posts IG de %s (max %d)...", profile_url, max_posts)

    run_input = {
        "directUrls": [profile_url],
        "resultsLimit": max_posts,
        "resultsType": "posts",
    }

    try:
        run = client.actor(APIFY_IG_POSTS).call(
            run_input=run_input,
            timeout_secs=300,
        )
    except Exception as e:
        log.warning("  Erreur découverte posts IG : %s", e)
        return []

    post_urls = []
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        url = item.get("url") or item.get("shortCode")
        if url:
            if not url.startswith("http"):
                url = f"https://www.instagram.com/p/{url}/"
            post_urls.append(url)

    log.info("  → %d posts IG découverts", len(post_urls))
    return post_urls


def collect_instagram_comments(
    client,
    post_urls: list[str],
    brand_name: str,
    cfg: dict,
) -> list[dict]:
    """Collecte les commentaires d'une liste de posts Instagram."""
    if not post_urls:
        return []

    max_comments = cfg.get("max_comments_per_post", 500)
    delay = cfg.get("delay_between_calls", 2)
    max_retries = cfg.get("max_retries", 3)

    all_comments = []

    for i, url in enumerate(post_urls, 1):
        log.info("  [%d/%d] Collecte IG : %s", i, len(post_urls), url[:80])

        run_input = {
            "directUrls": [url],
            "resultsLimit": max_comments,
        }

        for attempt in range(1, max_retries + 1):
            try:
                run = client.actor(APIFY_IG_COMMENTS).call(
                    run_input=run_input,
                    timeout_secs=300,
                )
                break
            except Exception as e:
                log.warning("    Tentative %d/%d échouée : %s", attempt, max_retries, e)
                if attempt == max_retries:
                    log.error("    Abandon pour ce post après %d tentatives.", max_retries)
                    continue
                time.sleep(delay * attempt)

        try:
            for item in client.dataset(run["defaultDatasetId"]).iterate_items():
                text = (item.get("text") or "").strip()
                if not text:
                    continue

                all_comments.append({
                    "text": text,
                    "brand": brand_name,
                    "platform": "instagram",
                    "date": item.get("timestamp", ""),
                    "likes": item.get("likesCount", 0),
                    "replies_count": item.get("repliesCount", 0),
                    "author": item.get("ownerUsername", ""),
                    "comment_url": "",
                    "post_url": url,
                    "is_reply": bool(item.get("replyToId")),
                    "collected_at": datetime.now(timezone.utc).isoformat(),
                })
        except Exception as e:
            log.warning("    Erreur lecture résultats IG : %s", e)

        if i < len(post_urls):
            time.sleep(delay)

    log.info("  → %d commentaires Instagram collectés pour %s", len(all_comments), brand_name)
    return all_comments


# ---------------------------------------------------------------------------
# Nettoyage léger
# ---------------------------------------------------------------------------

def clean_text(text: str) -> str | None:
    """Nettoyage minimal du texte d'un commentaire."""
    if not text or len(text.strip()) < 3:
        return None

    text = re.sub(r"http\S+|www\.\S+", "", text)       # URLs
    text = re.sub(r"@\w+", "", text)                     # Mentions
    text = re.sub(r"\s+", " ", text).strip()              # Espaces multiples

    if len(text) < 3:
        return None

    return text


def deduplicate(comments: list[dict]) -> list[dict]:
    """Supprime les doublons exacts basés sur un hash du texte + auteur."""
    seen: set[str] = set()
    unique = []
    for c in comments:
        key = hashlib.md5(f"{c['text']}|{c['author']}".encode()).hexdigest()
        if key not in seen:
            seen.add(key)
            unique.append(c)
    removed = len(comments) - len(unique)
    if removed > 0:
        log.info("Doublons supprimés : %d", removed)
    return unique


# ---------------------------------------------------------------------------
# Sauvegarde
# ---------------------------------------------------------------------------

FIELDNAMES = [
    "text", "brand", "platform", "date", "likes", "replies_count",
    "author", "comment_url", "post_url", "is_reply", "collected_at",
]


def save_brand_csv(comments: list[dict], output_dir: Path, brand_name: str) -> Path:
    """Sauvegarde les commentaires d'une marque en CSV."""
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r"[^a-zA-Z0-9_]", "_", brand_name.lower())
    ts = datetime.now().strftime("%Y%m%d")
    path = output_dir / f"{safe_name}_{ts}.csv"

    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(comments)

    log.info("Sauvegardé : %s (%d lignes)", path, len(comments))
    return path


def save_merged_csv(comments: list[dict], path: Path) -> Path:
    """Sauvegarde tous les commentaires dans un seul CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(comments)

    log.info("Fichier fusionné : %s (%d lignes)", path, len(comments))
    return path


def save_stats(all_comments: list[dict], brands_stats: dict, path: Path):
    """Sauvegarde les statistiques de collecte en JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)

    stats = {
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "total_comments": len(all_comments),
        "by_brand": brands_stats,
        "by_platform": {
            "facebook": sum(1 for c in all_comments if c["platform"] == "facebook"),
            "instagram": sum(1 for c in all_comments if c["platform"] == "instagram"),
        },
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    log.info("Statistiques : %s", path)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def collect_brand(
    client,
    brand: dict,
    cfg: dict,
    platform_filter: str | None,
    dry_run: bool,
) -> list[dict]:
    """Collecte tous les commentaires FB + IG d'une marque."""
    name = brand["name"]
    comments: list[dict] = []

    log.info("=" * 60)
    log.info("Marque : %s", name)
    log.info("=" * 60)

    # --- Facebook ---
    if platform_filter in (None, "facebook"):
        fb_page = brand.get("facebook_page")
        fb_posts = brand.get("facebook_posts") or []

        if fb_page or fb_posts:
            if dry_run:
                log.info("  [DRY-RUN] Facebook — page=%s, posts=%d", fb_page, len(fb_posts))
            else:
                # Découvrir les posts si on n'a pas de liste explicite
                if not fb_posts and fb_page:
                    fb_posts = discover_facebook_posts(
                        client, fb_page, cfg.get("max_posts_per_page", 50)
                    )

                fb_comments = collect_facebook_comments(client, fb_posts, name, cfg)
                comments.extend(fb_comments)
        else:
            log.info("  Pas de page Facebook configurée.")

    # --- Instagram ---
    if platform_filter in (None, "instagram"):
        ig_profile = brand.get("instagram_profile")
        ig_posts = brand.get("instagram_posts") or []

        if ig_profile or ig_posts:
            if dry_run:
                log.info("  [DRY-RUN] Instagram — profile=%s, posts=%d", ig_profile, len(ig_posts))
            else:
                if not ig_posts and ig_profile:
                    ig_posts = discover_instagram_posts(
                        client, ig_profile, cfg.get("max_posts_per_page", 50)
                    )

                ig_comments = collect_instagram_comments(client, ig_posts, name, cfg)
                comments.extend(ig_comments)
        else:
            log.info("  Pas de profil Instagram configuré.")

    # Nettoyage léger
    cleaned = []
    for c in comments:
        clean = clean_text(c["text"])
        if clean:
            c["text"] = clean
            cleaned.append(c)

    log.info("  Total après nettoyage : %d (brut : %d)", len(cleaned), len(comments))
    return cleaned


def main():
    parser = argparse.ArgumentParser(
        description="RamyPulse — Collecteur de commentaires Facebook & Instagram",
    )
    parser.add_argument(
        "--brand", type=str, default=None,
        help="Collecter une seule marque (ex: 'Ramy', 'Ifri')",
    )
    parser.add_argument(
        "--platform", type=str, choices=["facebook", "instagram"], default=None,
        help="Collecter uniquement Facebook ou Instagram",
    )
    parser.add_argument(
        "--config", type=str, default=None,
        help="Chemin vers targets.yaml (défaut : même dossier que le script)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Afficher ce qui serait collecté sans lancer Apify",
    )
    args = parser.parse_args()

    # Charger la config
    config_path = Path(args.config) if args.config else None
    config = load_config(config_path)
    brands = config.get("brands", [])
    cfg = config.get("collection", {})
    output_cfg = config.get("output", {})

    raw_dir = SCRIPT_DIR / output_cfg.get("raw_dir", "output/raw")
    merged_path = SCRIPT_DIR / output_cfg.get("merged_file", "output/all_comments.csv")
    stats_path = SCRIPT_DIR / output_cfg.get("stats_file", "output/collection_stats.json")

    # Filtrer par marque si demandé
    if args.brand:
        brands = [b for b in brands if b["name"].lower() == args.brand.lower()]
        if not brands:
            log.error("Marque '%s' introuvable dans targets.yaml", args.brand)
            sys.exit(1)

    log.info("╔══════════════════════════════════════════════════════════╗")
    log.info("║       RamyPulse — Collecte de commentaires             ║")
    log.info("╚══════════════════════════════════════════════════════════╝")
    log.info("Marques    : %s", ", ".join(b["name"] for b in brands))
    log.info("Plateforme : %s", args.platform or "toutes")
    log.info("Dry-run    : %s", args.dry_run)
    log.info("")

    # Initialiser Apify (sauf dry-run)
    client = None
    if not args.dry_run:
        client = get_apify_client()

    # Collecter marque par marque
    all_comments: list[dict] = []
    brands_stats: dict[str, dict] = {}

    for brand in brands:
        brand_comments = collect_brand(client, brand, cfg, args.platform, args.dry_run)
        all_comments.extend(brand_comments)
        brands_stats[brand["name"]] = {
            "total": len(brand_comments),
            "facebook": sum(1 for c in brand_comments if c["platform"] == "facebook"),
            "instagram": sum(1 for c in brand_comments if c["platform"] == "instagram"),
        }

    if args.dry_run:
        log.info("\n[DRY-RUN] Aucune collecte effectuée. Vérifiez la config ci-dessus.")
        return

    # Déduplication globale
    all_comments = deduplicate(all_comments)

    # Sauvegarder par marque
    for brand in brands:
        brand_data = [c for c in all_comments if c["brand"] == brand["name"]]
        if brand_data:
            save_brand_csv(brand_data, raw_dir, brand["name"])

    # Sauvegarder le fichier fusionné
    save_merged_csv(all_comments, merged_path)

    # Sauvegarder les stats
    save_stats(all_comments, brands_stats, stats_path)

    # Résumé final
    log.info("")
    log.info("╔══════════════════════════════════════════════════════════╗")
    log.info("║                    RÉSUMÉ FINAL                        ║")
    log.info("╠══════════════════════════════════════════════════════════╣")
    for name, s in brands_stats.items():
        log.info("║  %-20s FB: %-6d  IG: %-6d  Total: %-6d ║", name, s["facebook"], s["instagram"], s["total"])
    log.info("╠══════════════════════════════════════════════════════════╣")
    log.info("║  TOTAL : %-6d commentaires                            ║", len(all_comments))
    log.info("╚══════════════════════════════════════════════════════════╝")


if __name__ == "__main__":
    main()
