#!/usr/bin/env python3
"""Construit le kit de validation humaine du gold V0.3.

Conception. Deux risques distincts, deux echantillons :

  1. DESACCORDS entre A3 et C — dit lequel des deux avait raison.
  2. ACCORDS entre A3 et C — seul moyen de detecter un biais PARTAGE.
     Si les deux LLM se trompent de la meme facon, l'accord inter-annotateurs
     ne le verra jamais. C'est le point aveugle de toute la demarche.

Presentation uniforme et melangee : le relecteur voit toujours UNE annotation
et juge si elle est correcte, sans savoir si les annotateurs etaient d'accord.
Montrer les deux versions sur les desaccords biaiserait vers l'arbitrage et
montrer l'accord biaiserait vers l'acceptation.

Usage : python scripts/build_human_validation_kit.py
"""
from __future__ import annotations

import json
import random
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CP = ROOT / 'data/processed/slm_v2_gold/campaign_v0.2'
OUT = ROOT / 'data/processed/slm_v2_gold/human_validation_v0.3'
SEED = 20260731
N_DISAGREE = 30
N_AGREE = 30

CRITICAL = ['is_exploitable', 'business_relevance', 'sentiment.label', 'aspects', 'alerts']


def load(folder: str) -> dict:
    d = {}
    for p in sorted((CP / folder).glob('batch_*.out.jsonl')):
        for line in p.read_text(encoding='utf-8').splitlines():
            if line.strip():
                r = json.loads(line)
                d[r['record_id']] = r
    return d


def key(r: dict, field: str):
    if field == 'sentiment.label':
        return r['sentiment']['label']
    if field == 'aspects':
        return tuple(sorted((a['family'], a['sentiment']) for a in r['aspects']))
    if field == 'alerts':
        return tuple(sorted((a['type'], a['severity']) for a in r['alerts']))
    return r[field]


def render(rid: str, item: dict, ann: dict, n: int) -> str:
    mt = ann['monitoring_target']
    cible = f"{mt['scope']}" + (f" — {mt['entity_name']}" if mt.get('entity_name') else '')
    asp = ann['aspects'] or []
    alr = ann['alerts'] or []
    txt = item['text']
    if len(txt) > 400:   # textes repetitifs : montrer assez pour juger, pas noyer
        txt = txt[:350] + f'\n[… tronque, {len(txt)} caracteres au total, contenu repetitif]'
    lines = [
        f'## {n}. `{rid}`', '',
        '```text', txt, '```', '',
        f'- Cible surveillée : **{cible}**',
        f"- Auteur : **{ann['author_role']}**"
        + ('  · contexte parent requis' if ann.get('requires_parent_context') else ''),
        f"- Exploitable : **{ann['is_exploitable']}**"
        + (f" ({ann['non_exploitable_reason']})" if ann.get('non_exploitable_reason') else ''),
        f"- Pertinence business : **{ann['business_relevance']}**",
        f"- Langue : **{ann['language']['dominant']}**",
        f"- Sentiment : **{ann['sentiment']['label']}** / {ann['sentiment']['intensity']}"
        f" / {ann['sentiment']['emotion']}"
        + ('  · sarcasme' if ann['sentiment'].get('sarcasm') else ''),
        f"  - preuves : {ann['sentiment']['evidence'] or '—'}",
        f"- Intentions : **{', '.join(ann['intents']) or '—'}**",
        '- Aspects : ' + ('**—**' if not asp else ''),
    ]
    for a in asp:
        lines.append(f"  - **{a['family']}** · {a['sentiment']} · {a['intensity']}"
                     f" — preuves {a['evidence']}")
    lines.append('- Alertes : ' + ('**—**' if not alr else ''))
    for a in alr:
        lines.append(f"  - **{a['type']}** · {a['severity']} — preuves {a['evidence']}")
    lines += ['', '**Verdict** — remplace une seule case par `x` :', '',
              '- [ ] correcte',
              '- [ ] acceptable, nuance discutable',
              '- [ ] INCORRECTE',
              '',
              'Si incorrecte, dis en une ligne ce qui devrait changer :', '',
              '> ', '', '---', '']
    return '\n'.join(lines)


def main() -> int:
    rng = random.Random(SEED)
    OUT.mkdir(parents=True, exist_ok=True)
    A, C = load('output_a'), load('output_c')
    items = {r['record_id']: r for p in sorted((CP / 'input').glob('batch_*.jsonl'))
             for r in (json.loads(l) for l in p.read_text(encoding='utf-8').splitlines() if l.strip())}
    ids = sorted(set(A) & set(C))

    disagree, agree = [], []
    for i in ids:
        diff = [f for f in CRITICAL if key(A[i], f) != key(C[i], f)]
        (disagree if diff else agree).append((i, diff))
    print(f'items : {len(ids)}  desaccord sur un champ critique : {len(disagree)}  accord total : {len(agree)}')

    # Desaccords : couvrir tous les champs, pas seulement le plus frequent.
    by_field: dict[str, list] = {f: [] for f in CRITICAL}
    for i, diff in disagree:
        by_field[diff[0]].append(i)
    picked: list[str] = []
    for f in CRITICAL:
        v = by_field[f][:]
        rng.shuffle(v)
        picked += v[:max(2, N_DISAGREE // len(CRITICAL))]
    rest = [i for i, _ in disagree if i not in picked]
    rng.shuffle(rest)
    picked = (picked + rest)[:N_DISAGREE]

    # Accords : tirage aleatoire stratifie par scope, pour detecter le biais partage.
    ag = [i for i, _ in agree]
    org = [i for i in ag if A[i]['monitoring_target']['scope'] == 'organisation']
    pub = [i for i in ag if A[i]['monitoring_target']['scope'] != 'organisation']
    rng.shuffle(org); rng.shuffle(pub)
    picked_ag = org[:N_AGREE // 2] + pub[:N_AGREE - N_AGREE // 2]

    kit = []
    for i in picked:
        src = rng.choice(['A3', 'C'])          # aleatoire : ne pas privilegier un annotateur
        kit.append({'record_id': i, 'groupe': 'desaccord', 'annotation_montree': src,
                    'ann': (A if src == 'A3' else C)[i]})
    for i in picked_ag:
        src = rng.choice(['A3', 'C'])          # identiques par construction
        kit.append({'record_id': i, 'groupe': 'accord', 'annotation_montree': src,
                    'ann': (A if src == 'A3' else C)[i]})
    rng.shuffle(kit)                            # le relecteur ignore le groupe

    md = ['# Validation humaine — gold V0.3', '',
          f'{len(kit)} commentaires a relire. Compte environ 45 minutes.', '',
          'Pour chaque item : le texte, puis **une** annotation produite par le systeme.',
          'Dis simplement si elle est correcte. Tu ne sais pas — volontairement — si les',
          'deux annotateurs automatiques etaient d accord sur cet item. C est ce qui permet',
          'de detecter une erreur qu ils partagent tous les deux.', '',
          'Ne cherche pas la perfection : juge si un responsable metier accepterait cette',
          'annotation telle quelle.', '',
          'Reference des valeurs autorisees :',
          '`data/processed/slm_v2_gold/campaign_v0.2/VOCABULAIRES_FERMES_V0.2.md`', '',
          '---', '']
    for n, e in enumerate(kit, 1):
        md.append(render(e['record_id'], items[e['record_id']], e['ann'], n))
    (OUT / 'REVUE_HUMAINE.md').write_text('\n'.join(md), encoding='utf-8')

    # La cle reste separee : le relecteur ne doit pas pouvoir la consulter.
    (OUT / '_cle_ne_pas_ouvrir.json').write_text(json.dumps(
        [{'n': n, 'record_id': e['record_id'], 'groupe': e['groupe'],
          'annotation_montree': e['annotation_montree']} for n, e in enumerate(kit, 1)],
        ensure_ascii=False, indent=1), encoding='utf-8')

    print(f"\nkit ecrit : {(OUT / 'REVUE_HUMAINE.md').relative_to(ROOT)}")
    print(f"  {sum(e['groupe'] == 'desaccord' for e in kit)} desaccords, "
          f"{sum(e['groupe'] == 'accord' for e in kit)} accords, melanges")
    print('  champs couverts par les desaccords :',
          dict(Counter(next(f for f in CRITICAL if key(A[e['record_id']], f) != key(C[e['record_id']], f))
                       for e in kit if e['groupe'] == 'desaccord')))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
