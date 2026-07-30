#!/usr/bin/env python3
"""Dépouille la repasse arabizi et décide si la correction a marché.

Trois verdicts indépendants, tous nécessaires :
  1. l'étape de lecture a-t-elle été faite (lecture_fr rempli) ;
  2. le repli sur `neutre` a-t-il reculé sur l'arabizi ;
  3. la passe a-t-elle SURCORRIGÉ — les témoins non arabizi, déjà validés par
     l'humain, ont-ils basculé sans raison.

Le point 3 est le plus important : un prompt qui dit « ne dis pas neutre »
produit facilement un gain apparent en cassant tout le reste.
"""
import json, sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / 'data/processed/slm_v2_gold/arabizi_repass_v0.3'

def main() -> int:
    key = json.loads((D / '_cle_ne_pas_ouvrir.json').read_text(encoding='utf-8'))
    new = {}
    for p in sorted((D / 'output').glob('batch_*.out.jsonl')):
        for line in p.read_text(encoding='utf-8').splitlines():
            if line.strip():
                r = json.loads(line)
                new[r['record_id']] = r
    if not new:
        print('Aucune sortie dans output/. Lance la passe d abord.')
        return 1
    azi, tem = key['arabizi'], key['temoins']
    ref, verite = key['temoins_reference'], key['verite_terrain_humaine']
    print(f'items recus : {len(new)} / {len(azi) + len(tem)}')

    miss = [i for i in new if not str(new[i].get('lecture_fr', '')).strip()]
    print(f"\n1. ETAPE DE LECTURE  : {len(new) - len(miss)}/{len(new)} traductions remplies")
    if miss:
        print(f'   MANQUANTES : {miss[:10]}')

    a = [i for i in azi if i in new]
    nz = sum(new[i]['sentiment']['label'] == 'neutre' for i in a) / len(a)
    before = key['taux_neutre_arabizi_avant']
    noasp = sum(not new[i]['aspects'] for i in a) / len(a)
    print(f'\n2. REPLI SUR NEUTRE  : {before:.0%} -> {nz:.0%}  ({nz - before:+.0%})')
    print(f'   sans aspect       : 56% -> {noasp:.0%}')
    print(f'   repartition       : {dict(Counter(new[i]["sentiment"]["label"] for i in a))}')

    t = [i for i in tem if i in new]
    flip = [(i, ref[i]['sentiment'], new[i]['sentiment']['label'])
            for i in t if new[i]['sentiment']['label'] != ref[i]['sentiment']]
    nflip = [x for x in flip if x[1] == 'neutre']
    print(f'\n3. SURCORRECTION     : {len(flip)}/{len(t)} temoins ont change')
    print(f'   dont neutres bascules : {len(nflip)}/{sum(1 for i in t if ref[i]["sentiment"] == "neutre")}')
    for x in flip[:8]:
        print(f'     {x[0]} : {x[1]} -> {x[2]}')

    print('\n4. CONTROLE DUR (verite humaine)')
    hard = 0
    for rid, exp in verite.items():
        if rid not in new:
            print(f'   {rid} : ABSENT'); continue
        got = new[rid]['sentiment']['label']
        ok = got == exp['sentiment']
        line = f"   {rid} : attendu {exp['sentiment']:8s} obtenu {got:8s} {'OK' if ok else 'RATE'}"
        if 'alerte' in exp:
            al = [x['type'] for x in new[rid]['alerts']]
            aok = exp['alerte'] in al
            line += f" | alerte {exp['alerte']} : {'OK' if aok else 'ABSENTE'}"
            ok = ok and (aok or new[rid]['monitoring_target']['scope'] != 'organisation')
        hard += ok
        print(line)

    print('\n=== VERDICT ===')
    ok_read = not miss
    ok_gain = nz <= before - 0.10
    ok_stable = len(nflip) <= 2
    ok_hard = hard >= 2
    for label, v in [('etape de lecture faite', ok_read), ('repli reduit d au moins 10 pts', ok_gain),
                     ('pas de surcorrection des temoins', ok_stable), ('controle dur passe', ok_hard)]:
        print(f'  [{"OK " if v else "NON"}] {label}')
    if all((ok_read, ok_gain, ok_stable, ok_hard)):
        print('\nRepasse ACCEPTEE : les 41 items arabizi peuvent remplacer les anciens.')
        return 0
    print('\nRepasse REFUSEE : ne pas integrer, corriger la consigne et relancer.')
    return 2

if __name__ == '__main__':
    raise SystemExit(main())
