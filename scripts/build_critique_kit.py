#!/usr/bin/env python3
"""Construit le lot soumis a la critique independante.

Deux principes de conception.

**Le doute du producteur n'est pas montre.** Le professeur signale lui-meme les
annotations qu'il juge injustifiables. Si le critique voyait ce drapeau, son
accord ne prouverait rien — c'est le meme piege que l'accord entre deux
annotateurs qui partagent un biais. Les items signales sont donc melanges aux
autres, sans marque. On mesure ensuite si le critique les retrouve seul.

**L'echantillon est stratifie sur ce qui fait varier la difficulte** : le niveau
de complexite, la presence d'une alerte, et la langue. Un tirage uniforme
donnerait un lot domine par les avis francais simples, qui sont les plus nombreux
et les moins informatifs.

Les cas a severite elevee ne passent pas par ici : l'audit les envoie en revue
humaine, pas a un modele.

Usage :
  python scripts/build_critique_kit.py [--n 300]
"""
from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/processed/slm_v2_gold/maps_v0.3'
SEED = 20260812
BATCH = 25


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--n', type=int, default=300)
    args = ap.parse_args()
    rng = random.Random(SEED)

    traces = {}
    for f in sorted((BASE / 'holdout/traces').glob('*.trace.jsonl')):
        for ligne in f.read_text(encoding='utf-8').splitlines():
            if ligne.strip():
                r = json.loads(ligne)
                traces[r['record_id']] = r
    annotations = {}
    for f in sorted((BASE / 'holdout/output').glob('*.out.jsonl')):
        for ligne in f.read_text(encoding='utf-8').splitlines():
            if ligne.strip():
                r = json.loads(ligne)
                annotations[r['record_id']] = r
    textes = {}
    for f in sorted((BASE / 'holdout/input').glob('*.jsonl')):
        for ligne in f.read_text(encoding='utf-8').splitlines():
            if ligne.strip():
                r = json.loads(ligne)
                textes[r['record_id']] = r['text']

    ids = [i for i in traces if i in annotations and i in textes]
    if not ids:
        print('aucune trace enrichie disponible')
        return 1

    # Les items que le professeur a lui-meme signales entrent tous : ce sont eux
    # qui mesurent si le critique detecte sans qu'on lui souffle la reponse.
    signales = [i for i in ids if not traces[i].get('justifiable', True)]

    def strate(rid: str) -> tuple:
        t = traces[rid]['decision_trace']
        return (t['complexity']['level'],
                bool(t['decisions']['alerts']),
                (annotations[rid].get('language') or {}).get('dominant'))

    par_strate = defaultdict(list)
    for i in ids:
        if i not in signales:
            par_strate[strate(i)].append(i)
    for v in par_strate.values():
        rng.shuffle(v)

    choisis = list(signales)
    strates = sorted(par_strate, key=lambda s: (-len(par_strate[s]), str(s)))
    k = 0
    while len(choisis) < args.n and any(par_strate[s] for s in strates):
        s = strates[k % len(strates)]
        if par_strate[s]:
            choisis.append(par_strate[s].pop())
        k += 1
    rng.shuffle(choisis)

    entree = BASE / 'critique/input'
    entree.mkdir(parents=True, exist_ok=True)
    (BASE / 'critique/output').mkdir(parents=True, exist_ok=True)
    items = []
    for rid in choisis:
        t = traces[rid]
        a = annotations[rid]
        items.append({
            'record_id': rid,
            'texte': textes[rid],
            'annotation': {
                'is_exploitable': a['is_exploitable'],
                'business_relevance': a['business_relevance'],
                'sentiment': a['sentiment'],
                'aspects': a['aspects'],
                'alerts': a['alerts'],
                'entities': a['entities'],
                'intents': a['intents'],
            },
            'compact_trace': t['compact_trace'],
            'uncertainties': t['decision_trace']['uncertainties'],
        })

    for i in range(0, len(items), BATCH):
        (entree / f'batch_{i // BATCH + 1:02d}.jsonl').write_text(
            ''.join(json.dumps(x, ensure_ascii=False) + '\n' for x in items[i:i + BATCH]),
            encoding='utf-8')

    (BASE / 'critique/_cle_ne_pas_ouvrir.json').write_text(json.dumps(
        {'seed': SEED, 'signales_par_le_professeur': sorted(signales),
         'total': len(items)}, ensure_ascii=False, indent=1), encoding='utf-8')

    # Le drapeau du professeur ne doit apparaitre nulle part dans les lots.
    blob = ''.join(p.read_text(encoding='utf-8') for p in entree.glob('batch_*.jsonl'))
    # Chercher la CLE JSON, pas le mot : « probleme » apparait legitimement dans
    # le texte d'une incertitude ecrite en francais.
    fuites = [m for m in ('justifiable', 'probleme', 'stars', 'weak_labels')
              if f'"{m}"' in blob]

    print(f'lot de critique : {len(items)} items, '
          f'{(len(items) + BATCH - 1) // BATCH} lots de {BATCH}')
    print(f'  dont signales par le professeur : {len(signales)} (non identifies dans le lot)')
    print(f'  complexite : {dict(Counter(traces[i]["decision_trace"]["complexity"]["level"] for i in choisis))}')
    print(f'  avec alerte: {sum(bool(annotations[i]["alerts"]) for i in choisis)}')
    print(f'  langues    : {dict(Counter((annotations[i].get("language") or {}).get("dominant") for i in choisis).most_common(5))}')
    print(f'  fuite      : {fuites or "aucune"}')
    print(f'  ecrit dans   {entree.relative_to(ROOT)}')
    return 1 if fuites else 0


if __name__ == '__main__':
    raise SystemExit(main())
