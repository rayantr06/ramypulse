#!/usr/bin/env python3
"""Assemble le jeu d'entrainement depuis un objet maitre unique.

L'audit du 29 juillet impose cette forme : « Les vues `compact_trace + JSON`,
taches auxiliaires et controle `JSON only` sont construites depuis cet objet
maitre. Elles ne doivent pas devenir des copies independantes difficiles a
synchroniser. » Toutes les vues sont donc derivees ici, en un seul passage.

Trois garanties de construction.

**Le holdout et le gold n'entrent jamais dans l'entrainement.** Ce n'est pas une
consigne mais une exclusion par identifiant : les deux ensembles sont charges,
et tout exemple qui s'y trouve est ecarte avant l'ecriture. C'est ce qui rend
l'evaluation valide — le professeur ayant annote les deux de la meme facon,
l'eleve paraitrait bien meilleur qu'il n'est.

**Rien d'invalide n'entre.** Une trace qui echoue au schema, une annotation dont
une preuve n'existe pas dans le texte, une trace hors budget apres compression :
ecartees et comptees. La politique d'evaluation compte deja une sortie invalide
comme fausse ; l'entrainer serait apprendre a en produire.

**Le split est stratifie et reproductible.** Sur la langue et la presence
d'alerte, aux deux endroits ou un tirage uniforme deforme : l'arabizi est rare,
et les alertes le sont encore plus.

Usage :
  python scripts/build_training_set.py --sources <dir traces> [--sources ...] \
                                       --output <dir> [--seed 20260812]
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from validate_annotations import (  # noqa: E402
    attributs_autorises, deriver_actionability, nettoyer_attribut,
    resoudre_entite, resoudre_offsets,
)

SCHEMA = ROOT / 'docs/slm_v2/business_comment_annotation_v0.4.schema.json'
#: Ensembles reserves a l'evaluation. Jamais d'entrainement, sans exception.
RESERVES = (
    ROOT / 'data/processed/slm_v2_gold/maps_v0.3/holdout/output',
    ROOT / 'data/processed/slm_v2_gold/gold_v0.4',
)
HORS_CONTRAT = ('record_id', 'annotator', 'notes', 'lecture_fr')


def identifiants_reserves() -> set[str]:
    """Charge les identifiants a exclure. Une exclusion par appartenance vaut
    mieux qu'une consigne : elle ne peut pas etre oubliee."""
    reserves: set[str] = set()
    for chemin in RESERVES:
        if not chemin.exists():
            continue
        for f in sorted(chemin.glob('*.jsonl')):
            for ligne in f.read_text(encoding='utf-8').splitlines():
                if ligne.strip():
                    reserves.add(json.loads(ligne)['record_id'])
    return reserves


def annotation_finale(brut: dict, texte: str, attendus: dict, version: str) -> dict:
    """Reconstitue l'annotation telle que le pipeline la produit : offsets
    resolus, `actionability` derivee, attribut hors liste retire."""
    a = {k: v for k, v in brut.items() if k not in HORS_CONTRAT}
    a['schema_version'] = version
    for bloc in ([a.get('sentiment') or {}] + (a.get('aspects') or [])
                 + (a.get('alerts') or [])):
        if 'evidence' in bloc:
            bloc['evidence'] = resoudre_offsets(bloc['evidence'], texte)
    for entite in a.get('entities') or []:
        resoudre_entite(entite, texte)
    for aspect in a.get('aspects') or []:
        nettoyer_attribut(aspect, attendus)
    a['actionability'] = deriver_actionability(a)
    return a


def texte_entrainement(texte: str, contexte: dict, trace: str, annotation: dict) -> str:
    """Vue principale : trace compacte puis JSON.

    Le contexte de surveillance est dans l'entree, pas dans la cible : l'eleve le
    recevra en production, il n'a pas a le deviner.
    """
    cible = contexte.get('monitoring_target') or {}
    entete = (f"scope={cible.get('scope')}"
              + (f" entite={cible.get('entity_name')}" if cible.get('entity_name') else '')
              + (f" secteur={contexte.get('topic')}" if contexte.get('topic') else ''))
    return (f'### Contexte ###\n{entete}\n\n'
            f'### Commentaire ###\n{texte}\n\n'
            f'### Raisonnement ###\n{trace}\n\n'
            f'### Annotation ###\n'
            f'{json.dumps(annotation, ensure_ascii=False, separators=(",", ":"))}')


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--sources', action='append', required=True,
                    help='dossier de traces enrichies (.trace.jsonl), repetable')
    ap.add_argument('--texts', action='append', required=True)
    ap.add_argument('--annotations', action='append', required=True)
    ap.add_argument('--output', required=True)
    ap.add_argument('--seed', type=int, default=20260812)
    ap.add_argument('--part-dev', type=float, default=0.05)
    args = ap.parse_args()
    rng = random.Random(args.seed)

    import jsonschema
    schema = json.loads(SCHEMA.read_text(encoding='utf-8'))
    version = schema['properties']['schema_version']['const']
    valideur = jsonschema.Draft202012Validator(schema)
    attendus = attributs_autorises(schema)

    def charger(dossiers, motif):
        rows = {}
        for d in dossiers:
            p = Path(d)
            for f in (sorted(p.glob(motif)) if p.is_dir() else [p]):
                for ligne in f.read_text(encoding='utf-8').splitlines():
                    if ligne.strip():
                        r = json.loads(ligne)
                        rows[r['record_id']] = r
        return rows

    entrees = charger(args.texts, '*.jsonl')
    annotations = charger(args.annotations, '*.out.jsonl')
    traces = charger(args.sources, '*.trace.jsonl')
    reserves = identifiants_reserves()

    exemples, rejets = [], Counter()
    for rid, trace in traces.items():
        if rid in reserves:
            rejets['reserve_evaluation'] += 1
            continue
        if rid not in entrees or rid not in annotations:
            rejets['source_manquante'] += 1
            continue
        t = trace['decision_trace']
        if not t['validation'].get('schema_valid'):
            rejets['trace_invalide'] += 1
            continue
        if not t['validation'].get('within_token_budget'):
            rejets['hors_budget'] += 1
            continue
        texte = entrees[rid]['text']
        if not all(e['text'] == texte[e['start']:e['end']] for e in t['evidence_map']):
            rejets['preuve_non_ancree'] += 1
            continue

        annotation = annotation_finale(annotations[rid], texte, attendus, version)
        if next(valideur.iter_errors(annotation), None):
            rejets['annotation_invalide'] += 1
            continue

        contexte = entrees[rid].get('context') or {}
        contexte['monitoring_target'] = entrees[rid].get('monitoring_target')
        exemples.append({
            'example_id': rid,
            'text': texte,
            'context': contexte,
            'annotation': annotation,
            'decision_trace': t,
            'compact_trace': trace['compact_trace'],
            'training_text': texte_entrainement(texte, contexte,
                                                trace['compact_trace'], annotation),
            'source_provenance': {'source': contexte.get('source'),
                                  'secteur': contexte.get('topic'),
                                  'ville': contexte.get('city')},
            'generation_provenance': t['provenance'],
            'validation': {**t['validation'],
                           'annotation_schema_valid': True,
                           'compression': trace.get('compression') or []},
            'split': None,
        })

    # Split stratifie : l'arabizi et les alertes sont rares, un tirage uniforme
    # laisserait le dev sans exemplaire de l'un ou de l'autre.
    par_strate = defaultdict(list)
    for e in exemples:
        par_strate[((e['annotation'].get('language') or {}).get('dominant'),
                    bool(e['annotation'].get('alerts')))].append(e)
    for groupe in par_strate.values():
        rng.shuffle(groupe)
        n_dev = max(1, round(len(groupe) * args.part_dev)) if len(groupe) > 4 else 0
        for i, e in enumerate(groupe):
            e['split'] = 'dev' if i < n_dev else 'train'

    sortie = Path(args.output)
    sortie.mkdir(parents=True, exist_ok=True)
    rng.shuffle(exemples)
    for split in ('train', 'dev'):
        lot = [e for e in exemples if e['split'] == split]
        (sortie / f'master_{split}.jsonl').write_text(
            ''.join(json.dumps(e, ensure_ascii=False) + '\n' for e in lot), encoding='utf-8')
        # Vue principale d'entrainement.
        (sortie / f'sft_trace_json_{split}.jsonl').write_text(
            ''.join(json.dumps({'text': e['training_text']}, ensure_ascii=False) + '\n'
                    for e in lot), encoding='utf-8')
        # Controle d'ablation : meme entree, sans raisonnement. Il sert a mesurer
        # ce que la trace apporte reellement, pas a la remplacer.
        (sortie / f'sft_json_only_{split}.jsonl').write_text(
            ''.join(json.dumps({'text': e['training_text'].split('### Raisonnement ###')[0]
                                + '### Annotation ###\n'
                                + json.dumps(e['annotation'], ensure_ascii=False,
                                             separators=(',', ':'))},
                               ensure_ascii=False) + '\n' for e in lot), encoding='utf-8')

    train = [e for e in exemples if e['split'] == 'train']
    dev = [e for e in exemples if e['split'] == 'dev']
    print(f'traces lues      : {len(traces)}')
    print(f'exemples retenus : {len(exemples)}')
    for motif, n in rejets.most_common():
        print(f'  ecarte {n:6d}  {motif}')
    print(f'\ntrain {len(train)}  ·  dev {len(dev)}')
    for nom, lot in (('train', train), ('dev', dev)):
        if not lot:
            continue
        langues = Counter((e['annotation'].get('language') or {}).get('dominant') for e in lot)
        print(f'  {nom:6s} alertes {sum(bool(e["annotation"]["alerts"]) for e in lot):5d}'
              f'  arabizi {langues.get("darija_arabizi", 0):4d}'
              f'  langues {len(langues)}')
    # Verification de l'exclusion : aucune fuite possible vers l'evaluation.
    fuite = {e['example_id'] for e in exemples} & reserves
    print(f'\nidentifiants reserves : {len(reserves)}')
    print(f'fuite vers l entrainement : {len(fuite)}')
    return 1 if fuite else 0


if __name__ == '__main__':
    raise SystemExit(main())
