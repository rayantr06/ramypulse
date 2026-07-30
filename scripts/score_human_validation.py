#!/usr/bin/env python3
"""Depouille les verdicts humains du kit de validation V0.3.

Le resultat qui compte n'est pas le taux global mais l'ecart entre les deux
groupes. Un taux d'erreur eleve sur les items ou les deux annotateurs etaient
D'ACCORD signale un biais partage : l'accord inter-annotateurs ne le detecte
jamais, et il se propagerait tel quel dans le modele entraine.
"""
import json, re, sys
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/processed/slm_v2_gold/human_validation_v0.3'

def main() -> int:
    md = (OUT / 'REVUE_HUMAINE.md').read_text(encoding='utf-8')
    key = {k['n']: k for k in json.loads((OUT / '_cle_ne_pas_ouvrir.json').read_text(encoding='utf-8'))}
    blocks = re.split(r'^## (\d+)\. ', md, flags=re.M)[1:]
    verdicts, missing = {}, []
    for i in range(0, len(blocks), 2):
        n, body = int(blocks[i]), blocks[i + 1]
        got = [lab for lab, pat in [('correcte', r'- \[x\] correcte'),
                                     ('nuance', r'- \[x\] acceptable'),
                                     ('incorrecte', r'- \[x\] INCORRECTE')]
               if re.search(pat, body, re.I)]
        if len(got) != 1:
            missing.append(n); continue
        note = re.search(r'^> ?(.*)$', body, re.M)
        verdicts[n] = (got[0], (note.group(1).strip() if note else ''))
    print(f'items relus : {len(verdicts)}/{len(key)}')
    if missing:
        print(f'  non remplis ou cases multiples : {missing}')
    if not verdicts:
        print("\nAucun verdict. Coche une case par item en remplacant '- [ ]' par '- [x]'.")
        return 1
    print()
    rows = []
    for grp in ('accord', 'desaccord'):
        v = [verdicts[n] for n in verdicts if key[n]['groupe'] == grp]
        if not v: continue
        c = Counter(x[0] for x in v)
        ok = (c['correcte'] + c['nuance']) / len(v)
        rows.append((grp, len(v), c['correcte'], c['nuance'], c['incorrecte'], ok))
    print(f"{'groupe':12s} {'n':>4s} {'correcte':>9s} {'nuance':>7s} {'incorr.':>8s} {'acceptable':>11s}")
    for g, n, a, b, c, ok in rows:
        print(f'{g:12s} {n:>4d} {a:>9d} {b:>7d} {c:>8d} {ok:>10.0%}')
    d = {g: ok for g, _, _, _, _, ok in rows}
    if 'accord' in d and 'desaccord' in d:
        print(f"\necart accord - desaccord : {d['accord'] - d['desaccord']:+.0%}")
        if d['accord'] < 0.85:
            print("ALERTE — biais partage probable : les deux annotateurs se trompent ensemble.")
            print("         L accord inter-annotateurs surestime la qualite du gold.")
        else:
            print("Pas de biais partage detectable : l accord inter-annotateurs est un")
            print("indicateur de qualite credible sur cet echantillon.")
    print('\ncorrections signalees :')
    for n in sorted(verdicts):
        lab, note = verdicts[n]
        if lab != 'correcte' and note:
            print(f"  [{key[n]['groupe']:9s}] {key[n]['record_id']} ({lab}) : {note}")
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
