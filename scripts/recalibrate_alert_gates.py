#!/usr/bin/env python3
"""Mesure si les portes d'alerte sont redevenues evaluables.

Le fichier de portes porte depuis juillet une condition bloquante :

    « Portes d'alerte NON EVALUABLES : 16 evenements distincts,
      IC 95 % [0,444 ; 0,931]. Le pool est epuise. »

Un intervalle large de 0,486 ne permet de rejeter aucune hypothese : un modele a
0,50 et un modele a 0,90 y sont indistinguables. Le corpus Maps change la donne.

Ce que ce script mesure. Le reechantillonnage se fait **par evenement**, pas par
instance : deux avis signalant la meme rupture de service chez le meme operateur
ne sont pas deux observations independantes. Compter les instances gonflerait
artificiellement la precision — c'est l'erreur que l'analyse de juillet avait
evitee, et qu'il ne faut pas reintroduire.

Un evenement est le couple (entite surveillee, type d'alerte).

Usage :
  python scripts/recalibrate_alert_gates.py --input <dir output> --texts <dir input>
"""
from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATES = ROOT / 'docs/slm_v2/gold_v0.1/baselines/acceptance_gates_v0.3.json'
SEED = 20260811
TIRAGES = 2000
#: Largeur d'IC au-dela de laquelle une porte ne discrimine plus rien.
LARGEUR_ACCEPTABLE = 0.20


def charger(chemin: Path) -> dict:
    rows = {}
    for f in sorted(chemin.glob('*.out.jsonl')) if chemin.is_dir() else [chemin]:
        for ligne in f.read_text(encoding='utf-8').splitlines():
            if ligne.strip():
                r = json.loads(ligne)
                rows[r['record_id']] = r
    return rows


def bootstrap_largeur(evenements: list, n: int, rng: random.Random) -> float:
    """Largeur de l'IC 95 % d'une proportion estimee sur `n` evenements tires."""
    if n < 2:
        return 1.0
    scores = []
    for _ in range(TIRAGES):
        tirage = [rng.choice(evenements) for _ in range(n)]
        scores.append(sum(tirage) / n)
    scores.sort()
    return scores[int(0.975 * TIRAGES)] - scores[int(0.025 * TIRAGES)]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', required=True)
    ap.add_argument('--texts', action='append', required=True)
    args = ap.parse_args()
    rng = random.Random(SEED)

    ann = charger(Path(args.input))
    contexte = {}
    for d in args.texts:
        p = Path(d)
        for f in (sorted(p.glob('*.jsonl')) if p.is_dir() else [p]):
            for ligne in f.read_text(encoding='utf-8').splitlines():
                if ligne.strip():
                    r = json.loads(ligne)
                    contexte[r['record_id']] = r.get('context') or {}

    # Un evenement = (entite, type). Deux avis sur la meme rupture ne sont pas
    # deux observations independantes.
    par_evenement: dict[tuple, list] = defaultdict(list)
    for rid, r in ann.items():
        for alerte in r.get('alerts') or []:
            cle = ((r.get('monitoring_target') or {}).get('entity_name'), alerte['type'])
            par_evenement[cle].append((rid, alerte))

    types = Counter(t for _, t in par_evenement)
    secteurs = {contexte.get(rid, {}).get('topic')
                for insts in par_evenement.values() for rid, _ in insts}

    print(f'items annotes          : {len(ann)}')
    print(f'instances d alerte     : {sum(len(v) for v in par_evenement.values())}')
    print(f'EVENEMENTS distincts   : {len(par_evenement)}   <- 16 en juillet')
    print(f'entites concernees     : {len({e for e, _ in par_evenement})}')
    print(f'secteurs concernes     : {len(secteurs)}')
    print(f'\ntypes exerces ({len(types)}/9) :')
    for t, n in types.most_common():
        print(f'  {t:30s} {n:4d} evenements')
    absents = {'qualite_produit', 'securite_sante', 'fraude_arnaque', 'juridique_conformite',
               'rupture_service', 'rupture_stock', 'reputation_virale',
               'donnees_confidentialite', 'harcelement_discrimination'} - set(types)
    print(f'  jamais exerces : {sorted(absents) or "aucun"}')

    # Precision atteignable : largeur de l'IC selon le nombre d'evenements. La
    # proportion simulee est fixee a 0,80, ordre de grandeur d'une porte d'alerte.
    print(f'\nlargeur de l IC 95 % selon le nombre d evenements (proportion 0,80) :')
    reference = [1] * 80 + [0] * 20
    for n in (16, 50, 100, 158, len(par_evenement), 500, 1000):
        if n > 2000:
            continue
        largeur = bootstrap_largeur(reference, n, rng)
        verdict = 'evaluable' if largeur <= LARGEUR_ACCEPTABLE else 'trop large'
        marque = '  <- disponible ici' if n == len(par_evenement) else ''
        print(f'  {n:5d} evenements -> largeur {largeur:.3f}  {verdict}{marque}')

    largeur_reelle = bootstrap_largeur(reference, len(par_evenement), rng)
    print(f'\nverdict : avec {len(par_evenement)} evenements, largeur {largeur_reelle:.3f}')
    if largeur_reelle <= LARGEUR_ACCEPTABLE:
        print('  Les portes d alerte redeviennent EVALUABLES.')
        print('  La condition bloquante de juillet peut etre levee.')
    else:
        print(f'  Encore insuffisant : il en faudrait davantage.')

    gates = json.loads(GATES.read_text(encoding='utf-8'))
    print('\nconditions bloquantes actuelles du fichier de portes :')
    for c in gates.get('blocking_conditions', []):
        print(f'  - {c[:110]}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
