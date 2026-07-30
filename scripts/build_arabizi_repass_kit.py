#!/usr/bin/env python3
"""Construit le kit de réannotation ciblée de l'arabizi (V0.3).

Problème traité. La relecture humaine a montré que les deux annotateurs se
replient sur `neutre` en arabizi : 54 % contre 41 % ailleurs, et 3 des 4 erreurs
franches. Ce n'est pas de la négligence mais un échec de déchiffrage — l'arabizi
encode l'arabe en caractères latins et chiffres, et un annotateur qui ne décode
pas voit du bruit et choisit le repli le plus sûr.

Intervention. Une étape de lecture explicite est rendue obligatoire : produire la
traduction française AVANT d'annoter. On ne demande pas de « faire attention »,
on impose l'étape qui manquait.

Garde-fous contre la surcorrection. Un prompt qui dit « ne dis pas neutre » fait
sur-attribuer du sentiment. Le kit mêle donc 20 témoins non arabizi déjà validés
comme corrects par l'humain, dont 16 authentiquement neutres. Si la nouvelle passe
les fait basculer, elle surcorrige et doit être rejetée.

Trois items ont une vérité terrain humaine et servent de contrôle dur.

Usage : python scripts/build_arabizi_repass_kit.py
"""
from __future__ import annotations

import json
import random
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CP = ROOT / 'data/processed/slm_v2_gold/campaign_v0.2'
OUT = ROOT / 'data/processed/slm_v2_gold/arabizi_repass_v0.3'
SEED = 20260801
N_TEMOINS = 20

# Verdicts humains du 2026-07-30. Non communiqués à l'annotateur.
VERITE = {
    'v02_0111': {'sentiment': 'positif'},
    'v02_0215': {'sentiment': 'negatif'},
    'v02_0120': {'sentiment': 'negatif', 'alerte': 'harcelement_discrimination'},
}


def load(folder: str) -> dict:
    d = {}
    for p in sorted((CP / folder).glob('batch_*.out.jsonl')):
        for line in p.read_text(encoding='utf-8').splitlines():
            if line.strip():
                r = json.loads(line)
                d[r['record_id']] = r
    return d


def main() -> int:
    rng = random.Random(SEED)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'input').mkdir(exist_ok=True)
    (OUT / 'output').mkdir(exist_ok=True)

    sel = json.loads((CP.parent / '_azi_ids.json').read_text(encoding='utf-8'))
    A = load('output_a')
    items = {r['record_id']: r for p in sorted((CP / 'input').glob('batch_*.jsonl'))
             for r in (json.loads(l) for l in p.read_text(encoding='utf-8').splitlines() if l.strip())}

    azi = sel['arabizi']
    temoins = sel['temoins'][:]
    rng.shuffle(temoins)
    # Conserver la proportion de neutres : c'est eux qui détectent la surcorrection.
    neutres = [i for i in temoins if A[i]['sentiment']['label'] == 'neutre']
    autres = [i for i in temoins if A[i]['sentiment']['label'] != 'neutre']
    temoins = (neutres[:N_TEMOINS // 2] + autres[:N_TEMOINS - N_TEMOINS // 2])

    def ctx(i):
        # Le nom de source `dz_sentiment_mendeley_45k` contient le mot « sentiment »
        # et pourrait amorcer l'annotateur. Neutralisé, sans perte d'information utile.
        c = dict(items[i]['context'])
        if 'sentiment' in str(c.get('source', '')):
            c['source'] = 'corpus_public_dz'
        return c

    kit = [{'record_id': i, 'text': items[i]['text'],
            'monitoring_target': items[i]['monitoring_target'],
            'context': ctx(i)} for i in azi + temoins]
    rng.shuffle(kit)   # l'annotateur ignore quels items sont des témoins

    for n in range(0, len(kit), 21):
        p = OUT / 'input' / f'batch_{n // 21 + 1:02d}.jsonl'
        p.write_text(''.join(json.dumps(x, ensure_ascii=False) + '\n'
                             for x in kit[n:n + 21]), encoding='utf-8')

    (OUT / '_cle_ne_pas_ouvrir.json').write_text(json.dumps({
        'arabizi': azi, 'temoins': temoins,
        'temoins_reference': {i: {'sentiment': A[i]['sentiment']['label'],
                                  'langue': A[i]['language']['dominant']} for i in temoins},
        'verite_terrain_humaine': VERITE,
        'taux_neutre_arabizi_avant': round(
            sum(A[i]['sentiment']['label'] == 'neutre' for i in azi) / len(azi), 3),
    }, ensure_ascii=False, indent=1), encoding='utf-8')

    n_batches = (len(kit) + 20) // 21
    print(f'kit : {len(kit)} items — {len(azi)} arabizi + {len(temoins)} temoins')
    print(f'  temoins neutres : {sum(A[i]["sentiment"]["label"] == "neutre" for i in temoins)}'
          f' (detecteurs de surcorrection)')
    print(f'  lots : {n_batches} x 21')
    print(f'  taux de neutre arabizi avant : '
          f'{sum(A[i]["sentiment"]["label"] == "neutre" for i in azi) / len(azi):.0%}')
    print(f'  ecrit dans {OUT.relative_to(ROOT)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
