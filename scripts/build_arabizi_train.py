#!/usr/bin/env python3
"""Extrait la reserve d'arabizi des splits `train` des corpus linguistiques.

Pourquoi maintenant. L'arabizi est le coeur du produit — des commentaires
algeriens — et il ne pesait que 376 items sur 12 285 dans le jeu d'entrainement,
soit 3 %. C'est la langue ou le systeme a le plus echoue : les deux annotateurs
LLM s'y repliaient sur `neutre` dans 56 % des cas, et leur accord y etait le plus
eleve du corpus au moment ou leur validite etait la plus basse.

D'ou vient cette reserve. Le socle de validation avait ete tire exclusivement des
splits `dev` et `test`, pour qu'aucun item d'entrainement ne contamine
l'evaluation. Les splits `train` n'ont donc jamais ete touches : 3 248 items y
attendent, et c'est exactement leur destination.

Deux garanties conservees du socle :

1. **Aucune fuite.** Les splits `dev` et `test` restent hors de ce lot, et tout
   texte deja present dans le gold, le socle ou une campagne est ecarte.
2. **Etiquette faible cachee.** Mendeley et Hirak portent un sentiment. Il n'est
   pas montre a l'annotateur mais sert ensuite a detecter une derive sans
   relecture humaine — un item tres negatif annote `positif` se repere seul.

Ces corpus n'ont aucune marque surveillee : scope `espace_public` par la regle
D1, ce qui interdit les alertes. Le modele apprendra donc l'arabizi dans un
regime et la structure d'alerte dans l'autre, le scope etant donne en entree.

Usage : python scripts/build_arabizi_train.py [--n 3000]
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
OUT = GOLD / 'arabizi_train_v0.4'
SEED = 20260813
BATCH = 25

ARABIZI = re.compile(r'\b(?=[A-Za-z0-9]*[A-Za-z])(?=[A-Za-z0-9]*[2379])[A-Za-z0-9]{3,}\b')
ARABIC = re.compile(r'[؀-ۿ]')


def deja_vus() -> set[str]:
    """Tout texte deja utilise ailleurs, quel que soit son role."""
    vus: set[str] = set()
    for chemin in (GOLD / 'gold_v0.3/gold_v0.3.jsonl',
                   GOLD / 'campaign_v0.2/sample_full.jsonl',
                   GOLD / 'arabizi_repass_v0.3/input',
                   GOLD / 'arabizi_socle_v0.3/input'):
        if chemin.is_dir():
            fichiers = list(chemin.glob('*.jsonl'))
        elif chemin.exists():
            fichiers = [chemin]
        else:
            continue
        for f in fichiers:
            for ligne in f.read_text(encoding='utf-8').splitlines():
                if ligne.strip():
                    r = json.loads(ligne)
                    vus.add(r.get('text') or (r.get('annotation') or {}).get('text', ''))
    return vus


def etiquette_faible(row: dict) -> str | None:
    labels = row.get('task_labels') or {}
    for cle in ('sentiment_5_class', 'sentiment_binary'):
        val = labels.get(cle)
        if isinstance(val, dict):
            for k in ('normalized', 'label', 'value'):
                if val.get(k) is not None:
                    return str(val[k])
        elif val is not None:
            return str(val)
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--n', type=int, default=3000)
    args = ap.parse_args()
    rng = random.Random(SEED)
    (OUT / 'input').mkdir(parents=True, exist_ok=True)
    (OUT / 'output').mkdir(parents=True, exist_ok=True)

    vus = deja_vus()
    pool: dict[str, list] = defaultdict(list)
    for chemin in sorted(BASE.glob('*.jsonl')):
        for ligne in chemin.open(encoding='utf-8'):
            if not ligne.strip():
                continue
            r = json.loads(ligne)
            texte = r.get('text', '')
            # Splits `train` seulement : dev et test restent l'evaluation.
            if r.get('split') != 'train':
                continue
            if texte in vus or ARABIC.search(texte) or not ARABIZI.search(texte):
                continue
            if not (20 <= len(texte) <= 400):
                continue
            pool[chemin.stem].append(r)

    total = sum(len(v) for v in pool.values())
    print(f'arabizi disponible en split train : {total}')
    for source, rows in sorted(pool.items(), key=lambda x: -len(x[1])):
        print(f'   {source:30s} {len(rows):5d}')
    if not total:
        print('aucun item disponible', file=sys.stderr)
        return 1

    # Equilibrage par corpus puis par etiquette faible : sans cela le lot serait
    # domine par Mendeley et par une seule polarite.
    choisis: list[dict] = []
    par_source = max(1, args.n // len([v for v in pool.values() if v]))
    for source, rows in pool.items():
        par_etiquette: dict[str, list] = defaultdict(list)
        for r in rows:
            par_etiquette[str(etiquette_faible(r))].append(r)
        for v in par_etiquette.values():
            rng.shuffle(v)
        quota, etiquettes, i = par_source, [k for k in par_etiquette if par_etiquette[k]], 0
        while quota > 0 and etiquettes:
            cle = etiquettes[i % len(etiquettes)]
            if par_etiquette[cle]:
                choisis.append(par_etiquette[cle].pop())
                quota -= 1
                i += 1
            else:
                etiquettes.remove(cle)
    rng.shuffle(choisis)
    choisis = choisis[:args.n]

    items, cles = [], []
    for n, r in enumerate(choisis, 1):
        rid = f'azt_{n:05d}'
        items.append({
            'record_id': rid,
            'text': r['text'],
            'monitoring_target': {'scope': 'espace_public',
                                  'entity_name': None, 'entity_type': None},
            'context': {'source': 'corpus_public_dz',
                        'topic': (r.get('metadata') or {}).get('platform'), 'brand': None},
        })
        cles.append({'record_id': rid, 'corpus': (r.get('dataset') or {}).get('id'),
                     'split_origine': r.get('split'),
                     'etiquette_faible': etiquette_faible(r),
                     'licence': (r.get('dataset') or {}).get('licence')})

    for i in range(0, len(items), BATCH):
        (OUT / 'input' / f'batch_{i // BATCH + 1:04d}.jsonl').write_text(
            ''.join(json.dumps(x, ensure_ascii=False) + '\n' for x in items[i:i + BATCH]),
            encoding='utf-8')
    (OUT / '_cle_ne_pas_ouvrir.json').write_text(
        json.dumps({'seed': SEED, 'items': cles}, ensure_ascii=False), encoding='utf-8')

    # Chercher la CLE JSON, jamais le mot : « label » apparait legitimement dans
    # un commentaire algerien, et le detecteur avait deja crie sur « probleme ».
    blob = json.dumps(items, ensure_ascii=False)
    fuites = [m for m in ('sentiment', 'etiquette_faible', 'task_labels', 'split')
              if f'"{m}"' in blob]
    print(f'\nlot : {len(items)} items, {(len(items) + BATCH - 1) // BATCH} lots de {BATCH}')
    print('  par corpus    :', dict(Counter(c['corpus'] for c in cles)))
    print('  par etiquette :', dict(Counter(str(c['etiquette_faible']) for c in cles)))
    print(f'  fuite         : {fuites or "aucune"}')
    print(f'  ecrit dans      {OUT.relative_to(ROOT)}')
    return 1 if fuites else 0


if __name__ == '__main__':
    raise SystemExit(main())
