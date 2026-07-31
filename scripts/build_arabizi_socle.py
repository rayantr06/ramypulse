#!/usr/bin/env python3
"""Construit le socle d'annotation arabizi.

Pourquoi ce socle. C'est le seul blocage que ni Google Maps ni l'argent ne
resolvent. Maps ne donne que 5 % d'arabizi. La relecture humaine a montre que
les deux annotateurs automatiques s'y replient sur `neutre` — 54 % contre 41 %
ailleurs — et que leur accord y est le PLUS eleve du corpus alors que leur
validite y est la plus basse. Generer du synthetique sur cette base
amplifierait le defaut.

Il faut donc un socle arabizi valide avant toute generation a l'echelle.

Deux garanties de conception :

1. **Aucune fuite.** Les items sont tires exclusivement des splits `dev` et
   `test` des corpus linguistiques, deja exclus de l'entrainement. Les splits
   `train` ne sont pas touches.
2. **Verification integree.** Mendeley et Hirak portent une etiquette de
   sentiment. Elle n'est PAS montree a l'annotateur, mais sert ensuite a
   detecter automatiquement une derive : un item etiquete tres negatif et
   annote `positif` est une erreur reperable sans relecture humaine.

Usage : python scripts/build_arabizi_socle.py [--n 300]
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/processed/slm_v2_corpora/v0.1/normalized'
GOLD = ROOT / 'data/processed/slm_v2_gold'
OUT = GOLD / 'arabizi_socle_v0.3'
SEED = 20260731
BATCH = 25

ARABIZI = re.compile(r'\b(?=[A-Za-z0-9]*[A-Za-z])(?=[A-Za-z0-9]*[2379])[A-Za-z0-9]{3,}\b')
ARABIC = re.compile(r'[؀-ۿ]')
SOURCES = ('dz_sentiment_mendeley_45k', 'dz_sentiment_hirak_11760',
           'algd_toxicity_speech', 'narabizi_ud')


def already_used() -> set[str]:
    used: set[str] = set()
    for p in (GOLD / 'gold_v0.3/gold_v0.3.jsonl',
              GOLD / 'campaign_v0.2/sample_full.jsonl',
              GOLD / 'arabizi_repass_v0.3/input'):
        if p.is_dir():
            for f in p.glob('*.jsonl'):
                for line in f.read_text(encoding='utf-8').splitlines():
                    if line.strip():
                        used.add(json.loads(line)['text'])
        elif p.exists():
            for line in p.read_text(encoding='utf-8').splitlines():
                if line.strip():
                    used.add(json.loads(line)['text'])
    return used


def weak_label(row: dict) -> str | None:
    """Etiquette de sentiment du corpus d'origine, jamais montree a l'annotateur."""
    labels = row.get('task_labels') or {}
    for key in ('sentiment_5_class', 'sentiment_binary'):
        val = labels.get(key)
        if isinstance(val, dict):
            for k in ('normalized', 'label', 'value'):
                if val.get(k) is not None:
                    return str(val[k])
        elif val is not None:
            return str(val)
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--n', type=int, default=300)
    args = ap.parse_args()
    rng = random.Random(SEED)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'input').mkdir(exist_ok=True)
    (OUT / 'output').mkdir(exist_ok=True)

    used = already_used()
    pool: dict[str, list] = defaultdict(list)
    for source in SOURCES:
        p = BASE / f'{source}.jsonl'
        if not p.exists():
            continue
        for line in p.open(encoding='utf-8'):
            if not line.strip():
                continue
            r = json.loads(line)
            text = r['text']
            # Splits dev et test uniquement : jamais train, donc aucune fuite.
            if r.get('split') not in ('dev', 'test'):
                continue
            if text in used or ARABIC.search(text) or not ARABIZI.search(text):
                continue
            if not (20 <= len(text) <= 400):
                continue
            pool[source].append(r)

    total_dispo = sum(len(v) for v in pool.values())
    print(f'arabizi disponible en dev/test : {total_dispo}')
    for s, v in pool.items():
        print(f'   {s:28s} {len(v):5d}')
    if not total_dispo:
        print('aucun item disponible', file=sys.stderr)
        return 1

    # Equilibrage par corpus, puis par etiquette faible pour eviter un jeu
    # domine par une seule polarite.
    picked: list[dict] = []
    per_source = max(1, args.n // len([v for v in pool.values() if v]))
    for source, rows in pool.items():
        by_label: dict[str, list] = defaultdict(list)
        for r in rows:
            by_label[str(weak_label(r))].append(r)
        for v in by_label.values():
            rng.shuffle(v)
        quota = per_source
        labels = [k for k in by_label if by_label[k]]
        i = 0
        while quota > 0 and labels:
            label = labels[i % len(labels)]
            if by_label[label]:
                picked.append(by_label[label].pop())
                quota -= 1
            else:
                labels.remove(label)
                continue
            i += 1
    rng.shuffle(picked)
    picked = picked[:args.n]

    items, key = [], []
    for n, r in enumerate(picked, 1):
        rid = f'azi_{n:04d}'
        items.append({
            'record_id': rid,
            'text': r['text'],
            # Ces corpus n'ont aucune marque : scope espace_public par regle D1,
            # ce qui interdit les alertes et contraint la pertinence business.
            'monitoring_target': {'scope': 'espace_public',
                                  'entity_name': None, 'entity_type': None},
            'context': {'source': 'corpus_public_dz',
                        'topic': (r.get('metadata') or {}).get('platform'), 'brand': None},
        })
        key.append({'record_id': rid, 'corpus': r['dataset']['id'],
                    'split_origine': r.get('split'),
                    'etiquette_faible': weak_label(r),
                    'licence': (r.get('dataset') or {}).get('licence')})

    for i in range(0, len(items), BATCH):
        p = OUT / 'input' / f'batch_{i // BATCH + 1:02d}.jsonl'
        p.write_text(''.join(json.dumps(x, ensure_ascii=False) + '\n'
                             for x in items[i:i + BATCH]), encoding='utf-8')

    (OUT / '_cle_ne_pas_ouvrir.json').write_text(
        json.dumps({'seed': SEED, 'items': key}, ensure_ascii=False, indent=1), encoding='utf-8')

    # Aucune etiquette ne doit apparaitre dans les lots.
    blob = json.dumps(items, ensure_ascii=False)
    leaks = [w for w in ('sentiment', 'etiquette', 'toxic', 'label', 'negatif', 'positif')
             if w in blob.lower()]

    print(f'\nsocle : {len(items)} items, {(len(items) + BATCH - 1) // BATCH} lots de {BATCH}')
    print('  par corpus    :', dict(Counter(k['corpus'] for k in key)))
    print('  par etiquette :', dict(Counter(str(k['etiquette_faible']) for k in key)))
    print('  licences      :', dict(Counter(str(k['licence']) for k in key)))
    print(f'  fuite         : {leaks or "aucune"}')
    print(f'  ecrit dans      {OUT.relative_to(ROOT)}')
    return 1 if leaks else 0


if __name__ == '__main__':
    raise SystemExit(main())
