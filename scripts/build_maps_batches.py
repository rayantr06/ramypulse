#!/usr/bin/env python3
"""Prepare les lots d'annotation a partir du corpus Maps.

Trois decisions inscrites dans ce script.

1. **La note en etoiles ne part jamais avec le texte.** C'est le seul signal
   vraiment independant dont on dispose : il vient de l'auteur du commentaire,
   pas d'un annotateur de plateforme. Le montrer le detruirait — un desaccord
   entre l'annotation et une note que l'annotateur a lue ne vaut rien.

2. **Une tranche est reservee a l'evaluation avant toute annotation.** Le
   professeur annotera train et evaluation de la meme facon ; si la tranche
   d'evaluation reste telle quelle, l'eleve sera juge sur les biais de son
   propre professeur et paraitra meilleur qu'il n'est. Cette tranche doit
   passer par une relecture humaine avant de servir de reference.

3. **Stratification par secteur et par note.** Le corpus est domine par
   quelques secteurs ; un tirage uniforme donnerait un jeu d'evaluation
   ou les banques ecrasent tout le reste.

Usage :
  python scripts/build_maps_batches.py [--holdout 600] [--pilote 500]
"""
from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / 'data/processed/maps_corpus/maps_p1.jsonl'
BASE = ROOT / 'data/processed/slm_v2_gold/maps_v0.3'
SEED = 20260810
BATCH = 25
#: Champs retires avant envoi : ils porteraient la reponse ou des metadonnees inutiles.
A_RETIRER = ('weak_labels', 'published_at')


def ecrire_lots(items: list[dict], dossier: Path) -> int:
    dossier.mkdir(parents=True, exist_ok=True)
    for i in range(0, len(items), BATCH):
        lot = items[i:i + BATCH]
        (dossier / f'batch_{i // BATCH + 1:04d}.jsonl').write_text(
            ''.join(json.dumps(x, ensure_ascii=False) + '\n' for x in lot), encoding='utf-8')
    return (len(items) + BATCH - 1) // BATCH


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--holdout', type=int, default=600,
                    help="items reserves a l'evaluation, jamais utilises en entrainement")
    ap.add_argument('--pilote', type=int, default=500,
                    help='premiere tranche a annoter pour mesurer cout et qualite')
    args = ap.parse_args()
    rng = random.Random(SEED)

    lignes = [json.loads(l) for l in CORPUS.open(encoding='utf-8') if l.strip()]
    print(f'corpus : {len(lignes)} avis')

    # Strate = (secteur, polarite de la note). La note sert au tirage puis disparait.
    def strate(r: dict) -> tuple:
        etoiles = (r.get('weak_labels') or {}).get('stars')
        polarite = 'bas' if etoiles in (1, 2) else 'haut' if etoiles in (4, 5) else 'median'
        return ((r.get('context') or {}).get('topic') or 'inconnu', polarite)

    par_strate: dict[tuple, list] = defaultdict(list)
    for r in lignes:
        par_strate[strate(r)].append(r)
    for v in par_strate.values():
        rng.shuffle(v)

    # Tirage tournant sur les strates : chaque secteur est represente avant
    # qu'un secteur dominant ne prenne toute la place.
    holdout: list[dict] = []
    strates = sorted(par_strate, key=lambda k: (-len(par_strate[k]), str(k)))
    i = 0
    while len(holdout) < args.holdout and any(par_strate[s] for s in strates):
        s = strates[i % len(strates)]
        if par_strate[s]:
            holdout.append(par_strate[s].pop())
        i += 1

    reserves = {r['record_id'] for r in holdout}
    reste = [r for r in lignes if r['record_id'] not in reserves]
    rng.shuffle(reste)

    def nettoyer(r: dict) -> dict:
        """Retire la note en etoiles : c'est la reponse, elle ne part pas avec la question."""
        return {k: v for k, v in r.items() if k not in A_RETIRER}

    cles = {r['record_id']: {'stars': (r.get('weak_labels') or {}).get('stars'),
                             'secteur': (r.get('context') or {}).get('topic'),
                             'ville': (r.get('context') or {}).get('city')}
            for r in lignes}

    n_h = ecrire_lots([nettoyer(r) for r in holdout], BASE / 'holdout/input')
    pilote = reste[:args.pilote]
    n_p = ecrire_lots([nettoyer(r) for r in pilote], BASE / 'pilote/input')
    n_s = ecrire_lots([nettoyer(r) for r in reste[args.pilote:]], BASE / 'silver/input')

    BASE.mkdir(parents=True, exist_ok=True)
    (BASE / '_cle_ne_pas_ouvrir.json').write_text(json.dumps(
        {'seed': SEED, 'holdout': sorted(reserves), 'notes': cles},
        ensure_ascii=False), encoding='utf-8')

    # Aucune note ne doit subsister dans ce qui part a l'annotateur.
    fuites = [p.name for d in ('holdout', 'pilote', 'silver')
              for p in (BASE / d / 'input').glob('batch_*.jsonl')
              if '"stars"' in p.read_text(encoding='utf-8')]

    print(f"\nholdout : {len(holdout):5d} items, {n_h:3d} lots  (evaluation, relecture humaine requise)")
    print(f"pilote  : {len(pilote):5d} items, {n_p:3d} lots  (mesure cout et qualite)")
    print(f"silver  : {len(reste) - len(pilote):5d} items, {n_s:3d} lots  (entrainement)")
    print(f"\nsecteurs dans le holdout : {len({(cles[r['record_id']]['secteur']) for r in holdout})}")
    print(f"notes dans le holdout    : "
          f"{dict(sorted(Counter(cles[r['record_id']]['stars'] for r in holdout).items()))}")
    print(f"fuite d etoiles          : {fuites or 'aucune'}")
    return 1 if fuites else 0


if __name__ == '__main__':
    raise SystemExit(main())
