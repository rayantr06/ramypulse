#!/usr/bin/env python3
"""Migre le contrat en V0.4 : `hors_sujet` quitte les motifs de non-exploitabilite.

Decision D12. Mesuree, pas supposee.

Le professeur echouait quatre portes critiques contre le gold. La cause n'etait
pas sa qualite mais une ambiguite du contrat : `non_exploitable_reason:
hors_sujet` et `business_relevance: aucune` encodent le meme jugement, et rien
ne disait lequel employer. Sur les 19 desaccords du split dev, les deux
annotateurs disaient la meme chose dans deux champs differents.

Les deux encodages ne sont pourtant pas equivalents. `is_exploitable: false`
force `aspects` et `alerts` a rester vides : l'un jette le signal, l'autre le
garde. Sur 238 items de gold, 37 — 15,5 % — sont ainsi vides d'aspects par
construction.

Le principe qui tranche : tous les autres motifs decrivent le TEXTE — spam,
texte insuffisant, incomprehensible, bruit technique, langue non supportee,
ambiguite majeure. `hors_sujet` est le seul a decrire une RELATION entre le
texte et l'entite surveillee, ce que `business_relevance` encode deja. Et il est
indefini en scope `espace_public`, ou aucune entite n'est surveillee : 13 des 19
desaccords s'y trouvaient.

Ce que la migration ne peut pas faire. Re-encoder `is_exploitable` est sans
perte. Retrouver les aspects que l'ancien encodage avait supprimes ne l'est pas :
ils n'ont jamais ete annotes. Les 37 items concernes sont donc marques comme
demandant une reannotation de leurs aspects, plutot que presentes comme complets.

Usage : python scripts/migrate_v04.py
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs/slm_v2'
GOLD = ROOT / 'data/processed/slm_v2_gold/gold_v0.3'
SORTIE_GOLD = ROOT / 'data/processed/slm_v2_gold/gold_v0.4'
MOTIF_RETIRE = 'hors_sujet'


def construire_schema() -> dict:
    schema = json.loads(
        (DOCS / 'business_comment_annotation_v0.3.schema.json').read_text(encoding='utf-8'))
    schema['properties']['schema_version']['const'] = '0.4.0'
    motifs = schema['properties']['non_exploitable_reason']['enum']
    schema['properties']['non_exploitable_reason']['enum'] = [
        m for m in motifs if m != MOTIF_RETIRE]
    schema['properties']['non_exploitable_reason']['description'] = (
        "Motif de non-exploitabilite. Tous decrivent le TEXTE lui-meme. "
        "L'absence de rapport avec l'entite surveillee n'en est pas un : "
        "elle se dit dans `business_relevance`, qui n'empeche pas d'extraire "
        "les aspects.")
    schema['title'] = schema.get('title', 'business_comment_annotation') + ' v0.4'
    return schema


def migrer_annotation(annotation: dict) -> tuple[dict, bool]:
    """Re-encode un item `hors_sujet`. Retourne l'annotation et si elle a change."""
    if annotation.get('non_exploitable_reason') != MOTIF_RETIRE:
        annotation['schema_version'] = '0.4.0'
        return annotation, False
    annotation['is_exploitable'] = True
    annotation['non_exploitable_reason'] = None
    # `hors_sujet` disait deja qu'il n'y a pas de rapport : c'est `aucune`.
    annotation['business_relevance'] = 'aucune'
    annotation['schema_version'] = '0.4.0'
    return annotation, True


def main() -> int:
    schema = construire_schema()
    cible_schema = DOCS / 'business_comment_annotation_v0.4.schema.json'
    cible_schema.write_text(json.dumps(schema, ensure_ascii=False, indent=2) + '\n',
                            encoding='utf-8')
    print(f'schema ecrit : {cible_schema.relative_to(ROOT)}')
    print(f"  motifs restants : {schema['properties']['non_exploitable_reason']['enum']}")

    SORTIE_GOLD.mkdir(parents=True, exist_ok=True)
    stats = Counter()
    for nom in ('gold_v0.3.jsonl', 'gold_v0.3_dev.jsonl', 'gold_v0.3_test.jsonl'):
        source = GOLD / nom
        if not source.exists():
            continue
        lignes = []
        for ligne in source.read_text(encoding='utf-8').splitlines():
            if not ligne.strip():
                continue
            row = json.loads(ligne)
            row['annotation'], change = migrer_annotation(row['annotation'])
            if change:
                stats[nom] += 1
                # Ne pas presenter comme complet ce qui ne l'est pas : l'ancien
                # encodage interdisait les aspects, ils n'ont jamais ete annotes.
                row['aspects_a_reannoter'] = True
                row['confiance'] = 'migre_v04_aspects_manquants'
            lignes.append(row)
        cible = SORTIE_GOLD / nom.replace('v0.3', 'v0.4')
        cible.write_text(''.join(json.dumps(x, ensure_ascii=False) + '\n' for x in lignes),
                         encoding='utf-8')
        print(f'  {cible.name:24s} {len(lignes):4d} items, {stats[nom]:3d} migres')

    import jsonschema
    valideur = jsonschema.Draft202012Validator(schema)
    restants = invalides = 0
    for f in sorted(SORTIE_GOLD.glob('gold_v0.4*.jsonl')):
        for ligne in f.read_text(encoding='utf-8').splitlines():
            if not ligne.strip():
                continue
            a = json.loads(ligne)['annotation']
            if a.get('non_exploitable_reason') == MOTIF_RETIRE:
                restants += 1
            invalides += bool(next(valideur.iter_errors(a), None))
    print(f'\n`{MOTIF_RETIRE}` restants : {restants}')
    print(f'annotations invalides sous V0.4 : {invalides}')
    return 1 if restants or invalides else 0


if __name__ == '__main__':
    raise SystemExit(main())
