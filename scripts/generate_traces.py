#!/usr/bin/env python3
"""Produit une trace de raisonnement pour une annotation deja validee.

Pourquoi en arriere, et non pendant l'annotation. Nos etiquettes ne sont pas
definitives au moment ou elles sont posees : elles passent le controle des
etoiles, celui de DziriBERT, puis l'arbitrage. Une trace ecrite avant argumente
pour une etiquette qui peut encore changer — et l'eleve serait entraine sur un
raisonnement qui contredit sa cible. On ne paie donc la trace que sur ce qui a
survecu.

Les traces produites en arriere sont aussi plus propres : le modele connait deja
la conclusion, il n'y a ni impasse ni autocorrection dans le texte. C'est un
meilleur signal d'entrainement pour un petit modele.

Le risque de la methode, et sa parade. Un modele a qui l'on donne la reponse
fabrique une justification plausible meme pour une etiquette fausse. On lui
demande donc explicitement de signaler quand le texte ne permet PAS de justifier
l'etiquette : `justifiable: false` devient un detecteur d'erreur gratuit, qui
travaille sur des items que ni les etoiles ni DziriBERT n'examinent.

`lecture_fr` n'est pas regenere. Il a ete produit a l'annotation, ou il servait a
lire ; le reprendre ici reviendrait a le refaire dire par un modele qui connait
deja la reponse.

Usage :
  python scripts/generate_traces.py --input <dir annotations> --texts <dir source> \
                                    --output <dir traces>
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from annotate_vertex import appeler, charger_cle  # noqa: E402

#: Champs dont la trace doit rendre compte. Les autres sont mecaniques ou derives.
A_JUSTIFIER = ('sentiment', 'aspects', 'alerts', 'business_relevance', 'is_exploitable')

PROMPT = """Tu recois un commentaire algerien et son annotation, deja verifiee.

Ta tache n'est pas d'annoter : l'etiquetage est fait. Tu ecris le raisonnement qui
CONDUIT a cette annotation, tel qu'un annotateur competent l'aurait tenu.

## Ce que la trace doit faire

Elle explique les decisions qui demandent un jugement — le sentiment, les aspects,
les alertes, la pertinence business, l'exploitabilite. Elle s'appuie sur des
passages du texte, pas sur des generalites.

Elle est **compacte** : trois a six phrases. Pas de preambule, pas de resume de la
consigne, pas de reformulation de l'annotation en prose. Un lecteur doit comprendre
POURQUOI ces etiquettes et pas d'autres.

Quand une decision etait serree, dis ce qui a fait pencher, et ce qui a ete ecarte.

## Ce que tu dois signaler

Si le texte ne permet PAS de justifier une etiquette — si tu devrais inventer un
element absent pour y arriver — mets `justifiable` a `false` et nomme le champ en
cause dans `probleme`. Ne fabrique pas une justification plausible : c'est
exactement ce qu'on cherche a detecter.

Une etiquette defendable mais discutable reste `justifiable: true` ; la reserve se
dit dans la trace.

### Verification obligatoire avant d'ecrire la trace

Commence par relever, dans le texte, les expressions qui portent une **evaluation** :
insulte, eloge, remerciement, moquerie, plainte, enthousiasme, deception, jurons,
emojis affectifs, ponctuation d'exaspération.

Puis confronte ce relevé a l'etiquette :

- Le sentiment est `neutre` alors que tu as releve une expression evaluative ?
  **`justifiable: false`**. Ne cherche pas a expliquer pourquoi ce serait quand meme
  neutre — c'est le defaut le plus frequent et le plus coûteux de ce corpus, et il
  se presente toujours sous une justification raisonnable.
- `aspects` est vide alors que le texte critique ou loue quelque chose de precis ?
  **`justifiable: false`**.
- Le sentiment porte une polarite alors que tu n'as releve aucune evaluation — que
  des faits, une question, ou une formule de politesse inconditionnelle comme
  `Aid Moubarak` ou `bonne journee` ? **`justifiable: false`** aussi.

Un texte reellement neutre existe : question factuelle, information sans opinion,
salutation. Dans ce cas dis dans la trace ce que tu as cherche et n'as pas trouve.

## Sortie

Un objet JSON, sans texte autour :

{"record_id":"...","trace":"...","justifiable":true,"probleme":null}"""


def construire_demande(annotation: dict, texte: str) -> dict:
    """Ne montre que ce qui demande un jugement : la trace n'a pas a justifier
    la langue detectee ni les offsets, qui sont mecaniques."""
    utile = {k: v for k, v in annotation.items() if k in A_JUSTIFIER}
    return {'record_id': annotation['record_id'], 'texte': texte,
            'lecture_fr': annotation.get('lecture_fr', ''), 'annotation': utile}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', required=True)
    ap.add_argument('--texts', action='append', required=True)
    ap.add_argument('--output', required=True)
    ap.add_argument('--model', default='gemini-3-flash-preview')
    ap.add_argument('--workers', type=int, default=8)
    ap.add_argument('--limit', type=int, default=None)
    args = ap.parse_args()

    cle = charger_cle()
    textes: dict[str, str] = {}
    for dossier in args.texts:
        chemin = Path(dossier)
        for f in (sorted(chemin.glob('*.jsonl')) if chemin.is_dir() else [chemin]):
            for ligne in f.read_text(encoding='utf-8').splitlines():
                if ligne.strip():
                    r = json.loads(ligne)
                    if 'text' in r:
                        textes[r['record_id']] = r['text']

    sortie = Path(args.output)
    sortie.mkdir(parents=True, exist_ok=True)
    lots = sorted(Path(args.input).glob('*.out.jsonl'))
    if not lots:
        print(f'aucune annotation dans {args.input}', file=sys.stderr)
        return 1

    total = douteux = echecs = 0
    problemes: Counter[str] = Counter()
    for lot in lots:
        cible = sortie / lot.name.replace('.out.jsonl', '.traces.jsonl')
        annotations = [json.loads(l) for l in lot.read_text(encoding='utf-8').splitlines()
                       if l.strip()]
        annotations = [a for a in annotations if a['record_id'] in textes]
        if args.limit:
            annotations = annotations[:args.limit]
        if cible.exists():
            faits = {json.loads(l)['record_id']
                     for l in cible.read_text(encoding='utf-8').splitlines() if l.strip()}
            if faits >= {a['record_id'] for a in annotations}:
                continue

        def traiter(annotation: dict):
            demande = construire_demande(annotation, textes[annotation['record_id']])
            try:
                res = appeler(PROMPT, demande, args.model, cle, reflexion='low')
            except Exception as err:                        # noqa: BLE001
                return None, f'{type(err).__name__}: {err}'
            if not isinstance(res, dict) or not str(res.get('trace') or '').strip():
                return None, 'trace vide'
            res['record_id'] = annotation['record_id']
            return res, None

        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            resultats = list(pool.map(traiter, annotations))

        bons = [r for r, _ in resultats if r]
        cible.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in bons),
                         encoding='utf-8')
        total += len(bons)
        echecs += sum(1 for _, e in resultats if e)
        for r in bons:
            if not r.get('justifiable', True):
                douteux += 1
                problemes[str(r.get('probleme'))] += 1
        print(f'{lot.name:26s} {len(bons):3d} traces, '
              f'{sum(1 for r in bons if not r.get("justifiable", True)):2d} non justifiables')

    print(f'\ntraces : {total}, echecs {echecs}')
    print(f'annotations que le texte ne justifie pas : {douteux}'
          + (f' = {douteux / total:.1%}' if total else ''))
    if problemes:
        print('  champs en cause :', dict(problemes.most_common(8)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
