#!/usr/bin/env python3
"""Test de rendement : avis Google Maps contre commentaires de page de marque.

Question posee. Notre corpus vient de pages de marque, ou 41 % des items n'ont
aucun aspect. Les avis Maps sont-ils reellement plus riches, et de combien ?

Methode. Comparer les deux sources sur des indicateurs structurels objectifs,
mesurables sans annotation : longueur, part d'items trop courts pour porter un
jugement, presence de marqueurs evaluatifs, et pour Maps la distribution des
notes qui donne directement le taux de candidats-alerte.

Ces indicateurs sont des approximations. Ils ne remplacent pas une passe
d'annotation, mais ils sont symetriques entre les deux sources, donc l'ecart
qu'ils mesurent est interpretable.

Limite de l'API : Place Details ne renvoie que 5 avis par lieu.

Usage : python scripts/maps_yield_test.py [--places 40]
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
import time
from collections import Counter
from pathlib import Path

import config

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/processed/maps_yield_test'

# Requetes couvrant des secteurs absents du corpus actuel, tous en Algerie.
QUERIES = [
    ('restauration', ['restaurant Alger', 'pizzeria Oran', 'fast food Constantine',
                      'restaurant Annaba', 'cafe Alger centre']),
    ('sante', ['clinique privee Alger', 'cabinet dentaire Oran', 'laboratoire analyses Alger',
               'pharmacie Constantine']),
    ('auto_services', ['garage automobile Alger', 'concessionnaire Oran',
                       'controle technique Alger']),
    ('hotellerie', ['hotel Alger', 'hotel Oran', 'residence touristique Bejaia']),
    ('commerce', ['supermarche Alger', 'magasin electromenager Oran',
                  'magasin telephone Alger']),
    ('services_publics', ['agence bancaire Alger', 'bureau de poste Alger',
                          'agence Algerie Telecom Alger']),
    ('education', ['ecole privee Alger', 'auto ecole Oran']),
]

EVAL_MARKERS = [
    # francais
    'bon', 'bien', 'mauvais', 'excellent', 'nul', 'cher', 'rapide', 'lent', 'sale',
    'propre', 'accueil', 'service', 'qualite', 'qualité', 'prix', 'deçu', 'décu',
    'recommande', 'eviter', 'éviter', 'parfait', 'horrible', 'correct', 'attente',
    # darija / arabe courant
    'مليح', 'خايب', 'غالي', 'رخيص', 'نظيف', 'وسخ', 'بزاف', 'الخدمة', 'السعر', 'جودة',
    'mli7', 'khayb', 'ghali', 'bzf', 'nadif',
]
SHORT_CHARS = 30


def collect(n_places: int) -> list[dict]:
    import googlemaps
    key = (getattr(config, 'GOOGLE_MAPS_API_KEY', '') or '').strip()
    if not key:
        print('GOOGLE_MAPS_API_KEY absente', file=sys.stderr)
        raise SystemExit(1)
    gm = googlemaps.Client(key=key)

    flat = [(sector, q) for sector, qs in QUERIES for q in qs]
    per_query = max(1, n_places // len(flat) + 1)
    reviews, seen_places, calls = [], set(), 0

    for sector, query in flat:
        if len(seen_places) >= n_places:
            break
        try:
            search = gm.places(query=query)
            calls += 1
        except Exception as exc:
            print(f'  recherche echouee [{query}] : {type(exc).__name__}', file=sys.stderr)
            continue
        for place in (search.get('results') or [])[:per_query]:
            pid = place.get('place_id')
            if not pid or pid in seen_places or len(seen_places) >= n_places:
                continue
            seen_places.add(pid)
            try:
                detail = gm.place(place_id=pid, language='fr',
                                  fields=['name', 'rating', 'user_ratings_total', 'review'])
                calls += 1
            except Exception as exc:
                print(f'  detail echoue : {type(exc).__name__}', file=sys.stderr)
                continue
            res = detail.get('result') or {}
            for rev in res.get('reviews') or []:
                text = str(rev.get('text') or '').strip()
                if not text:
                    continue
                reviews.append({
                    'secteur': sector,
                    'lieu': res.get('name'),
                    'note_lieu': res.get('rating'),
                    'note_avis': rev.get('rating'),
                    'text': text,
                })
            time.sleep(0.15)
        print(f'  {sector:18s} {query[:34]:36s} lieux={len(seen_places):3d} avis={len(reviews):4d}')
    print(f'\nappels API : {calls}  (~{calls * 0.017:.2f} USD au tarif Place Details)')
    return reviews


def brand_comments(n: int) -> list[str]:
    """Commentaires de page de marque deja collectes, comme point de comparaison."""
    p = ROOT / 'data/processed/slm_v2_corpora/v0.1/normalized/ramypulse_business_seed_pool.jsonl'
    out = []
    for line in p.read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if r['metadata']['context'].get('brand'):
            out.append(r['text'])
        if len(out) >= n:
            break
    return out


def profile(name: str, texts: list[str]) -> dict:
    lengths = sorted(len(t) for t in texts)
    marked = sum(any(m in t.lower() for m in EVAL_MARKERS) for t in texts)
    short = sum(l < SHORT_CHARS for l in lengths)
    return {
        'source': name, 'n': len(texts),
        'longueur_mediane': statistics.median(lengths) if lengths else 0,
        'longueur_moyenne': round(statistics.mean(lengths), 1) if lengths else 0,
        'part_courts': round(short / len(texts), 3) if texts else 0,
        'part_marqueur_evaluatif': round(marked / len(texts), 3) if texts else 0,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--places', type=int, default=40)
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    print(f'=== COLLECTE MAPS (cible {args.places} lieux, 5 avis max par lieu) ===')
    reviews = collect(args.places)
    if not reviews:
        print('aucun avis collecte', file=sys.stderr)
        return 1
    (OUT / 'maps_reviews.jsonl').write_text(
        ''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in reviews), encoding='utf-8')

    maps_texts = [r['text'] for r in reviews]
    brand_texts = brand_comments(len(maps_texts))

    pm, pb = profile('avis Google Maps', maps_texts), profile('page de marque', brand_texts)
    print(f'\n=== COMPARAISON ({pm["n"]} vs {pb["n"]}) ===')
    print(f"{'indicateur':30s} {'Maps':>12s} {'page marque':>14s}")
    for lab, k, fmt in [('longueur mediane (car.)', 'longueur_mediane', '{:.0f}'),
                        ('longueur moyenne (car.)', 'longueur_moyenne', '{:.1f}'),
                        ('part < 30 caracteres', 'part_courts', '{:.0%}'),
                        ('part avec marqueur evaluatif', 'part_marqueur_evaluatif', '{:.0%}')]:
        print(f'{lab:30s} {fmt.format(pm[k]):>12s} {fmt.format(pb[k]):>14s}')

    notes = Counter(r['note_avis'] for r in reviews if r['note_avis'])
    total = sum(notes.values())
    print(f'\n=== NOTES DES AVIS MAPS (etiquette faible gratuite) ===')
    for n in (1, 2, 3, 4, 5):
        c = notes.get(n, 0)
        print(f'   {n} etoile{"s" if n > 1 else " "} : {c:4d}  {c / total:5.1%}' if total else '')
    low = notes.get(1, 0) + notes.get(2, 0)
    print(f'\n   candidats-alerte (1-2 etoiles) : {low} = {low / total:.1%}' if total else '')
    print(f'   secteurs couverts : {len(set(r["secteur"] for r in reviews))}')
    print(f'   lieux distincts   : {len(set(r["lieu"] for r in reviews))}')

    (OUT / 'rapport.json').write_text(json.dumps({
        'maps': pm, 'page_marque': pb,
        'notes': {str(k): v for k, v in sorted(notes.items())},
        'taux_candidats_alerte': round(low / total, 3) if total else 0,
        'secteurs': sorted(set(r['secteur'] for r in reviews)),
        'lieux': len(set(r['lieu'] for r in reviews)),
    }, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'\necrit dans {OUT.relative_to(ROOT)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
