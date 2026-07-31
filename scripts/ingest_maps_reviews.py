#!/usr/bin/env python3
"""Ingère les avis Google Maps produits par `gosom/google-maps-scraper`.

Quatre traitements que la sortie brute ne fait pas :

1. **Suppression des données personnelles.** Le scraper renvoie `Name`,
   `ProfilePicture` et `author_url` pour chaque avis, sans option pour les
   désactiver. Les retirer ici est notre responsabilité, pas une option.
2. **Déduplication sur `review_id`**, indispensable puisque les passes de langue
   ramènent les mêmes lieux.
3. **Écartement des traductions.** `text_translated` rempli signale un avis
   traduit vers la langue demandée : ce n'est pas le texte d'origine.
4. **Assignation de `monitoring_target`** en scope `organisation` — le lieu est
   l'entité surveillée — avec sa catégorie comme secteur.

Usage :
  python scripts/ingest_maps_reviews.py --input out_fr.json --input out_ar.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/processed/maps_corpus'

#: Champs porteurs de données personnelles, retirés sans exception.
PERSONAL_FIELDS = ('Name', 'ProfilePicture', 'author_url', 'Images')
URL_RE = re.compile(r'http\S+|www\.\S+')
MIN_CHARS = 10


def clean(text: object) -> str:
    normalized = re.sub(r'\s+', ' ', str(text or '')).strip()
    return URL_RE.sub('', normalized).strip()


def review_id(place_id: str, raw_id: str, text: str) -> str:
    return hashlib.sha256('|'.join((place_id, raw_id, text)).encode('utf-8')).hexdigest()[:32]


def convert(place: dict, review: dict) -> dict | None:
    text = clean(review.get('text_original') or review.get('Description'))
    if len(text) < MIN_CHARS:
        return None
    # Un avis traduit n'est pas le texte de l'auteur.
    if str(review.get('text_translated') or '').strip():
        return None

    raw_id = str(review.get('review_id') or '')
    place_id = str(place.get('cid') or place.get('place_id') or place.get('title') or '')
    addr = place.get('complete_address') or {}
    return {
        'record_id': review_id(place_id, raw_id, text),
        'text': text,
        'monitoring_target': {
            'scope': 'organisation',
            'entity_name': place.get('title'),
            'entity_type': 'organisation',
        },
        'context': {
            'source': 'google_maps',
            'topic': place.get('category'),
            'brand': place.get('title'),
            'categories': place.get('categories') or [],
            'city': addr.get('borough') or addr.get('city'),
            'country': addr.get('country'),
        },
        'weak_labels': {
            # La note est une etiquette faible gratuite : un 1 etoile annote
            # `positif` est une erreur detectable automatiquement.
            'stars': review.get('Rating') or review.get('rating_float'),
            'place_rating': place.get('review_rating'),
        },
        'declared_language': review.get('language'),
        'published_at': review.get('published_at'),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', action='append', required=True,
                    help='fichier JSON produit par le scraper (repetable)')
    ap.add_argument('--since', default=None,
                    help='ne garder que les avis publies apres cette date ISO')
    ap.add_argument('--out-name', default='maps_reviews.jsonl')
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    docs: dict[str, dict] = {}
    stats = Counter()
    for path in args.input:
        p = Path(path)
        if not p.exists():
            print(f'introuvable : {p}', file=sys.stderr)
            continue
        for line in p.read_text(encoding='utf-8').splitlines():
            if not line.strip():
                continue
            place = json.loads(line)
            stats['lieux'] += 1
            for review in place.get('user_reviews') or []:
                stats['avis_bruts'] += 1
                # Retrait des donnees personnelles avant tout autre traitement.
                for field in PERSONAL_FIELDS:
                    review.pop(field, None)
                doc = convert(place, review)
                if not doc:
                    stats['ecartes'] += 1
                    continue
                if args.since and str(doc.get('published_at') or '') < args.since:
                    stats['trop_anciens'] += 1
                    continue
                if doc['record_id'] in docs:
                    stats['doublons'] += 1
                    continue
                docs[doc['record_id']] = doc

    rows = list(docs.values())
    target = OUT / args.out_name
    target.write_text(''.join(json.dumps(d, ensure_ascii=False) + '\n' for d in rows),
                      encoding='utf-8')

    # Verification : aucune donnee personnelle ne doit subsister.
    blob = target.read_text(encoding='utf-8')
    leaks = [f for f in PERSONAL_FIELDS if f'"{f}"' in blob]
    stars = Counter(d['weak_labels']['stars'] for d in rows)
    low = sum(v for k, v in stars.items() if k in (1, 2))

    print(f"lieux lus          : {stats['lieux']}")
    print(f"avis bruts         : {stats['avis_bruts']}")
    print(f"  ecartes          : {stats['ecartes']} (vides, trop courts, traduits)")
    print(f"  doublons         : {stats['doublons']}")
    print(f"  trop anciens     : {stats['trop_anciens']}")
    print(f"avis conserves     : {len(rows)}")
    print(f"secteurs distincts : {len({d['context']['topic'] for d in rows})}")
    print(f"lieux distincts    : {len({d['context']['brand'] for d in rows})}")
    print(f"notes              : {dict(sorted(stars.items(), key=lambda x: str(x[0])))}")
    if rows:
        print(f"candidats-alerte   : {low} = {low / len(rows):.1%}")
    print(f"donnees personnelles residuelles : {leaks or 'aucune'}")
    print(f"\necrit : {target.relative_to(ROOT)}")
    return 1 if leaks else 0


if __name__ == '__main__':
    raise SystemExit(main())
