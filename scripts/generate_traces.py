#!/usr/bin/env python3
"""Back-reasoning du professeur : complete la trace canonique projetee.

Ce script produisait auparavant une trace en prose libre, a la maniere du script
public `synth-funder`. L'audit du 29 juillet avait deja tranche contre ce choix,
mesures a l'appui : sur les 200 traces publiques de PleIAs, aucune reference
n'est obligatoire entre une decision et un passage du texte, aucun plafond n'est
impose, et certaines traces contiennent des developpements plausibles mais non
necessaires au JSON. Pour un petit modele, c'est apprendre a inventer des
explications.

Le professeur ne recoit donc plus une page blanche. Il recoit la projection
deterministe et ne complete que ce qu'elle ne peut pas deriver :

- la **regle de decision** reellement appliquee, quand elle differe du cas par
  defaut : negation, comparaison, inference contextuelle, sarcasme inverse ;
- le **mode** d'une intention, explicite ou implicite ;
- les **incertitudes** effectivement rencontrees, avec leurs alternatives ;
- les **drapeaux de qualite** du texte.

Il ne reecrit aucune etiquette : les valeurs viennent de l'annotation acceptee,
et toute divergence est un defaut, pas une correction.

La garde contre la rationalisation est conservee et mesuree. Un modele a qui l'on
donne la reponse fabrique une justification plausible meme pour une etiquette
fausse ; il lui est demande de signaler quand le texte ne la justifie pas. Sur
des etiquettes deliberement inversees, la detection est de 6/6 ; sur un
aplatissement en `neutre` — le defaut le plus couteux du corpus — elle est de
7/8 apres durcissement, et le detecteur est lui-meme non deterministe. Il produit
une file de relecture, pas un verdict.

Usage :
  python scripts/generate_traces.py --input <dir traces projetees> \
                                    --texts <dir source> --output <dir enrichi>
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
from trace_projection import comprimer, compter_tokens  # noqa: E402

TRACE_SCHEMA = ROOT / 'docs/slm_v2/business_decision_trace_v0.2.schema.json'


def vocab(schema: dict, chemin: tuple) -> list:
    noeud = schema['$defs'][chemin[0]]['properties'][chemin[1]]
    return noeud.get('enum') or []


def construire_prompt(schema: dict) -> str:
    return f"""Tu completes une trace de decision deja projetee depuis une annotation
verifiee. Tu n'annotes pas : les etiquettes sont fixees et ne doivent pas changer.

## Ce que la projection a deja fait

Elle a extrait la carte de preuves, relie chaque decision a ses preuves, calcule
la complexite, et pose une regle par defaut deduite de l'etiquette elle-meme.

## Ce que toi seul peux fournir

1. **La regle reellement appliquee**, quand le defaut est faux. Une polarite peut
   venir d'une negation, d'une comparaison, d'un sarcasme qui inverse le sens, ou
   d'une inference contextuelle plutot que d'une mention directe.
2. **Le mode d'une intention** : `explicite` si elle est formulee, `implicite` si
   elle se deduit.
3. **Les incertitudes reelles** : ce sur quoi un annotateur competent aurait
   hesite, avec les alternatives considerees. N'en invente pas pour remplir.
4. **Les drapeaux de qualite** du texte, pris dans la liste ci-dessous. Aucun si
   le texte est propre.

## Vocabulaires fermes

- regle de sentiment : {', '.join(vocab(schema, ('sentiment_decision', 'rule')))}
- regle d aspect : {', '.join(vocab(schema, ('aspect_decision', 'rule')))}
- declencheur d alerte : {', '.join(vocab(schema, ('alert_decision', 'trigger')))}
- champ d incertitude : {', '.join(vocab(schema, ('uncertainty', 'field')))}
- confiance : {', '.join(vocab(schema, ('uncertainty', 'confidence')))}
- statut : {', '.join(vocab(schema, ('uncertainty', 'status')))}
- drapeau de qualite : {', '.join(schema['$defs']['scan']['properties']['quality_flags']['items']['enum'])}

## Verification obligatoire

Avant de repondre, releve dans le texte les expressions qui portent une
**evaluation** — insulte, eloge, remerciement, moquerie, plainte, deception —
puis confronte-les aux etiquettes :

- sentiment `neutre` alors que tu as releve une evaluation ? `justifiable: false`
- `aspects` vide alors que le texte loue ou critique quelque chose de precis ?
  `justifiable: false`
- une polarite alors que tu n'as releve qu'un fait, une question, ou une formule
  inconditionnelle comme `Aid Moubarak` ? `justifiable: false`

Ne cherche pas a expliquer pourquoi ce serait quand meme correct : c'est
exactement le defaut qu'on cherche a detecter, et il se presente toujours sous
une justification raisonnable. Nomme le champ en cause dans `probleme`.

## Sortie

Un objet JSON, sans texte autour. Les tableaux suivent l'ordre de la projection.

{{"sentiment_rule":"negation",
 "aspect_rules":["mention_directe","comparaison"],
 "alert_triggers":["incident_explicite"],
 "intent_modes":["explicite","implicite"],
 "quality_flags":[],
 "uncertainties":[{{"field":"sentiment","issue":"ironie possible sur 'super'",
   "alternatives":["positif","negatif"],"resolved_as":"negatif",
   "confidence":"moyenne","status":"resolved"}}],
 "justifiable":true,"probleme":null}}"""


def demande(ligne: dict, texte: str) -> dict:
    """Ce que voit le professeur : le texte, et la trace compacte projetee.

    La trace compacte suffit : elle porte deja les preuves, les decisions et
    leurs liens. Renvoyer aussi l'annotation complete serait redondant et
    doublerait le cout d'entree.
    """
    t = ligne['decision_trace']
    return {'texte': texte, 'projection': ligne['compact_trace'],
            'intents': [i['label'] for i in t['decisions']['intents']],
            'aspects': [f"{a['family']}:{a['sentiment']}" for a in t['decisions']['aspects']],
            'alerts': [a['type'] for a in t['decisions']['alerts']]}


def appliquer(ligne: dict, reponse: dict, schema) -> list[str]:
    """Reporte les completions dans la trace canonique. Retourne les rejets."""
    t = ligne['decision_trace']
    dec = t['decisions']
    rejets = []

    def poser(cible: dict, champ: str, valeur, autorise: list):
        if valeur in autorise:
            cible[champ] = valeur
        elif valeur is not None:
            rejets.append(f'{champ}={valeur!r}')

    poser(dec['overall_sentiment'], 'rule', reponse.get('sentiment_rule'),
          vocab(schema, ('sentiment_decision', 'rule')))
    for aspect, regle in zip(dec['aspects'], reponse.get('aspect_rules') or []):
        poser(aspect, 'rule', regle, vocab(schema, ('aspect_decision', 'rule')))
    for alerte, decl in zip(dec['alerts'], reponse.get('alert_triggers') or []):
        poser(alerte, 'trigger', decl, vocab(schema, ('alert_decision', 'trigger')))
    for intent, mode in zip(dec['intents'], reponse.get('intent_modes') or []):
        poser(intent, 'mode', mode, ['explicite', 'implicite'])

    autorises = schema['$defs']['scan']['properties']['quality_flags']['items']['enum']
    for f in (reponse.get('quality_flags') or []):
        if f not in autorises:
            rejets.append(f'quality_flag={f!r}')
    t['scan']['quality_flags'] = [f for f in (reponse.get('quality_flags') or [])
                                  if f in autorises][:5]
    champs = vocab(schema, ('uncertainty', 'field'))
    t['uncertainties'] = [u for u in (reponse.get('uncertainties') or [])
                          if isinstance(u, dict) and u.get('field') in champs][:5]
    t['provenance']['method'] = 'hybrid'
    return rejets


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', required=True, help='dossier des .trace.jsonl projetes')
    ap.add_argument('--texts', action='append', required=True)
    ap.add_argument('--output', required=True)
    ap.add_argument('--model', default='gemini-3-flash-preview')
    ap.add_argument('--workers', type=int, default=8)
    ap.add_argument('--limit', type=int, default=None)
    ap.add_argument('--tokenizer', default='Qwen/Qwen3-0.6B',
                    help='tokenizer pour recompter apres enrichissement')
    args = ap.parse_args()

    import jsonschema
    tokenizer = None
    if args.tokenizer:
        from transformers import AutoTokenizer
        tokenizer = AutoTokenizer.from_pretrained(args.tokenizer)
    schema = json.loads(TRACE_SCHEMA.read_text(encoding='utf-8'))
    valideur = jsonschema.Draft202012Validator(schema)
    prompt = construire_prompt(schema)
    cle = charger_cle()

    textes = {}
    for d in args.texts:
        p = Path(d)
        for f in (sorted(p.glob('*.jsonl')) if p.is_dir() else [p]):
            for ligne in f.read_text(encoding='utf-8').splitlines():
                if ligne.strip():
                    r = json.loads(ligne)
                    if 'text' in r:
                        textes[r['record_id']] = r['text']

    sortie = Path(args.output)
    sortie.mkdir(parents=True, exist_ok=True)
    total = douteux = invalides = echecs = 0
    rejets: Counter[str] = Counter()
    problemes: Counter[str] = Counter()

    for lot in sorted(Path(args.input).glob('*.trace.jsonl')):
        lignes = [json.loads(l) for l in lot.read_text(encoding='utf-8').splitlines()
                  if l.strip()]
        lignes = [l for l in lignes if l['record_id'] in textes]
        if args.limit:
            lignes = lignes[:max(0, args.limit - total)]
        if not lignes:
            continue

        def traiter(ligne: dict):
            try:
                r = appeler(prompt, demande(ligne, textes[ligne['record_id']]),
                            args.model, cle, reflexion='low')
            except Exception as err:                        # noqa: BLE001
                return ligne, f'{type(err).__name__}: {err}'
            if not isinstance(r, dict):
                return ligne, 'reponse non objet'
            for cause in appliquer(ligne, r, schema):
                rejets[cause.split('=')[0]] += 1
            ligne['justifiable'] = bool(r.get('justifiable', True))
            ligne['probleme'] = r.get('probleme')
            # La trace compacte est recompilee : les regles completees peuvent
            # changer ce qui s'y ecrit. Elle repasse par la compression, sans quoi
            # l'enrichissement ferait ressortir du budget les traces qui y etaient
            # rentrees.
            tr = ligne['decision_trace']
            plafond = tr['complexity']['max_trace_tokens']
            ligne['compact_trace'], _ = comprimer(tr, plafond, tokenizer)
            for drapeau in ('_compact_sans_attribut', '_compact_sans_intensite',
                            '_compact_aspects_masques'):
                tr.pop(drapeau, None)
            tr['complexity']['observed_trace_tokens'] = compter_tokens(
                ligne['compact_trace'], tokenizer)[0]
            tr['validation']['within_token_budget'] = (
                tr['complexity']['observed_trace_tokens'] <= plafond)
            return ligne, None

        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            resultats = list(pool.map(traiter, lignes))

        bons = []
        for ligne, erreur in resultats:
            if erreur:
                echecs += 1
                continue
            erreurs = list(valideur.iter_errors(ligne['decision_trace']))
            ligne['decision_trace']['validation']['schema_valid'] = not erreurs
            invalides += bool(erreurs)
            if not ligne.get('justifiable', True):
                douteux += 1
                problemes[str(ligne.get('probleme'))] += 1
            bons.append(ligne)
            total += 1

        (sortie / lot.name).write_text(
            ''.join(json.dumps(x, ensure_ascii=False) + '\n' for x in bons), encoding='utf-8')
        print(f'{lot.name:26s} {len(bons):3d} traces, '
              f'{sum(1 for b in bons if not b.get("justifiable", True)):2d} non justifiables')
        if args.limit and total >= args.limit:
            break

    print(f'\ntraces enrichies : {total}, echecs {echecs}, invalides {invalides}')
    if rejets:
        print(f'  valeurs hors vocabulaire rejetees : {dict(rejets)}')
    print(f'annotations que le texte ne justifie pas : {douteux}'
          + (f' = {douteux / total:.1%}' if total else ''))
    if problemes:
        print(f'  champs en cause : {dict(problemes.most_common(6))}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
