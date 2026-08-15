#!/usr/bin/env python3
"""Format de sortie de l'eleve : une trace sans perte, dont l'annotation se deduit.

Pourquoi ce format existe. Le benchmark de juillet fixe `max_output_tokens: 256`
et une reference mesuree a 127 tokens en moyenne, sur un CPU sans GPU generant
29 a 44 tokens par seconde. Le SLO est de 8 secondes au p95.

Le jeu d'entrainement assemble produisait 613 tokens de sortie en mediane — la
trace 157, le JSON 451. A 30 tokens par seconde, cela fait vingt secondes : le
SLO est manque d'un facteur deux a trois. Zero exemple sur 1 200 tenait dans le
budget.

Le JSON est le coupable, pas la trace. Noms de champs complets, objets imbriques,
offsets resolus, `schema_version`, `actionability` derivee : tout cela, le
pipeline sait le reconstruire. Le faire ecrire au modele coute la latence du
produit pour rien.

La solution retenue n'est pas d'ajouter un second format compact a cote de la
trace, mais de constater que **la trace contient deja presque toute
l'annotation**. Il lui manquait cinq choses : le role de l'auteur, le besoin de
contexte parent, le detail de langue, le nom d'entite, et le caractere implicite
d'un aspect. Une fois ajoutees, la trace devient sans perte et le JSON s'en
deduit. Le modele ne produit plus qu'une chose.

C'est le meme partage que pour les offsets, et pour la meme raison : ce que le
pipeline peut reconstruire sans ambiguite ne doit pas transiter par le modele.

Verification : `verifier_aller_retour` compare l'annotation d'origine a celle
reconstruite depuis la trace, champ par champ. Un format sans perte est un
format dont l'aller-retour est l'identite.

Usage :
  python scripts/wire_format.py --annotations <dir> --texts <dir>
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from validate_annotations import (  # noqa: E402
    deriver_actionability, resoudre_entite, resoudre_offsets,
)

BARRE = chr(92)


def echapper(valeur: str) -> str:
    """Protege les guillemets d'un nom ou d'un extrait.

    Quatre entites du holdout portent un nom qui en contient — `حلويات " شوكنافة "`
    — et cassaient le delimiteur. Un format sans perte doit survivre a son propre
    corpus, pas seulement au cas courant.
    """
    return str(valeur).replace(BARRE, BARRE * 2).replace('"', BARRE + '"')


def desechapper(valeur: str) -> str:
    return valeur.replace(BARRE + '"', '"').replace(BARRE * 2, BARRE)


#: Chaine entre guillemets, guillemets echappes admis.
CITATION = r'(?:[^"\\]|\\.)*'

SIGNE = {'positif': '+', 'negatif': '-', 'mixte': '±', 'neutre': '0'}
SIGNE_INV = {v: k for k, v in SIGNE.items()}
#: Abreviations des roles et des ecritures : un token chacune plutot que trois.
ROLE = {'consommateur': 'c', 'marque': 'm', 'moderateur': 'd', 'media': 'j',
        'institution': 'i', 'inconnu': '?'}
ROLE_INV = {v: k for k, v in ROLE.items()}
SCRIPT = {'arabe': 'a', 'latin': 'l', 'tifinagh': 't', 'chiffres': 'n', 'autre': 'x'}
SCRIPT_INV = {v: k for k, v in SCRIPT.items()}


def encoder(annotation: dict, texte: str) -> str:
    """Compile l'annotation en trace sans perte.

    Ce qui n'y figure pas est reconstruit par `decoder` : les positions depuis les
    extraits, `actionability` par derivation D2/D3, `schema_version` par le
    contrat, et `monitoring_target` qui vient de l'entree, pas de la sortie.
    """
    langue = annotation.get('language') or {}
    sentiment = annotation.get('sentiment') or {}
    lignes = []

    etat = ('exploitable' if annotation.get('is_exploitable')
            else f"non:{annotation.get('non_exploitable_reason')}")
    scripts = ''.join(SCRIPT.get(s, 'x') for s in langue.get('scripts') or [])
    detectees = '/'.join(langue.get('detected') or [])
    parent = '^' if annotation.get('requires_parent_context') else ''
    lignes.append(
        f"scan → {etat},{annotation.get('business_relevance')},"
        f"{langue.get('dominant')}[{detectees}|{scripts}"
        f"{'|cs' if langue.get('code_switching') else ''}],"
        f"{ROLE.get(annotation.get('author_role'), '?')}{parent}")

    # Carte de preuves : chaque extrait cite une fois, reference ensuite par id.
    carte, ids = {}, {}
    def enregistrer(bloc):
        sortie = []
        for e in resoudre_offsets(bloc.get('evidence'), texte):
            if e['text'] not in carte:
                carte[e['text']] = f'ev_{len(carte) + 1}'
            sortie.append(carte[e['text']])
        ids[id(bloc)] = sortie
        return sortie

    enregistrer(sentiment)
    for a in annotation.get('aspects') or []:
        enregistrer(a)
    for a in annotation.get('alerts') or []:
        enregistrer(a)
    for extrait, ident in carte.items():
        lignes.append(f'{ident}="{echapper(extrait)}"')

    for e in annotation.get('entities') or []:
        nom = e.get('name') or ''
        mention = e.get('mention')
        # La mention n'est ecrite que si elle differe du nom : le plus souvent
        # elle lui est identique, et la repeter coute pour rien.
        suffixe = f'~"{echapper(mention)}"' if mention and mention != nom else ''
        lignes.append(f'{e["id"]}:{e["type"]}:{e["source"]}="{echapper(nom)}"{suffixe}')

    for a in annotation.get('aspects') or []:
        cible = f"@{a['target_entity_id']}" if a.get('target_entity_id') else ''
        detail = f".{a['attribute']}" if a.get('attribute') else ''
        implicite = '~' if a.get('implicit') else ''
        preuves = '+'.join(ids.get(id(a)) or []) or 'ctx'
        lignes.append(f"{preuves} → {a['family']}{detail}{cible}"
                      f":{SIGNE[a['sentiment']]}{implicite}:{a['intensity']}")

    for a in annotation.get('alerts') or []:
        cible = f"@{a['target_entity_id']}" if a.get('target_entity_id') else ''
        preuves = '+'.join(ids.get(id(a)) or []) or 'ctx'
        lignes.append(f"{preuves} → !{a['type']}{cible}:{a['severity']}")

    cibles = ','.join(sentiment.get('target_entity_ids') or []) or '-'
    sarcasme = '!' if sentiment.get('sarcasm') else ''
    preuves = '+'.join(ids.get(id(sentiment)) or []) or 'ctx'
    lignes.append(f"{preuves} → sentiment:{SIGNE[sentiment['label']]}{sarcasme}"
                  f":{sentiment['intensity']}:{sentiment['emotion']}@{cibles}")
    lignes.append(f"∴ {','.join(annotation.get('intents') or ['autre'])}")
    return '<think>\n' + '\n'.join(lignes) + '\n</think>'


def decoder(trace: str, texte: str, monitoring_target: dict, version: str) -> dict:
    """Reconstruit l'annotation complete depuis la trace."""
    corps = trace.replace('<think>', '').replace('</think>', '').strip()
    lignes = [l.strip() for l in corps.splitlines() if l.strip()]
    preuves: dict[str, str] = {}
    entites, aspects, alertes = [], [], []
    sentiment: dict = {}
    intents: list[str] = []
    scan: dict = {}

    for ligne in lignes:
        if ligne.startswith('scan → '):
            m = re.match(r'scan → ([^,]+),([^,]+),([^\[]+)\[([^|]*)\|([^|\]]*)(\|cs)?\],(.)(\^?)',
                         ligne)
            if not m:
                continue
            etat, pertinence, dominante, detectees, scripts, cs, role, parent = m.groups()
            scan = {
                'is_exploitable': etat == 'exploitable',
                'non_exploitable_reason': None if etat == 'exploitable' else etat.split(':', 1)[1],
                'business_relevance': pertinence,
                'language': {'dominant': dominante,
                             'detected': [d for d in detectees.split('/') if d],
                             'code_switching': bool(cs),
                             'scripts': [SCRIPT_INV.get(c, 'autre') for c in scripts]},
                'author_role': ROLE_INV.get(role, 'inconnu'),
                'requires_parent_context': parent == '^',
            }
        elif re.match(r'^ev_\d+="', ligne):
            ident, extrait = ligne.split('=', 1)
            preuves[ident] = desechapper(extrait.strip('"'))
        elif re.match(r'^ent_\d+:', ligne):
            m = re.match(rf'^(ent_\d+):([a-z_]+):([a-z]+)="({CITATION})"'
                         rf'(?:~"({CITATION})")?$', ligne)
            if m:
                ident, typ, source, nom, mention = m.groups()
                nom = desechapper(nom)
                mention = desechapper(mention) if mention else None
                entites.append({'id': ident, 'type': typ, 'source': source, 'name': nom,
                                'mention': (mention or nom) if source == 'texte' else None,
                                'start': None, 'end': None})
        elif ' → sentiment:' in ligne:
            src, reste = ligne.split(' → sentiment:', 1)
            m = re.match(r'^(.)(!?):([a-z]+):([a-z_]+)@(.*)$', reste)
            if m:
                signe, sarcasme, intensite, emotion, cibles = m.groups()
                sentiment = {'label': SIGNE_INV.get(signe, 'neutre'), 'intensity': intensite,
                             'emotion': emotion, 'sarcasm': sarcasme == '!',
                             'target_entity_ids': [c for c in cibles.split(',') if c != '-' and c],
                             'evidence': [preuves[i] for i in src.split('+') if i in preuves]}
        elif ' → !' in ligne:
            src, reste = ligne.split(' → !', 1)
            m = re.match(r'^([a-z_]+)(?:@(ent_\d+))?:([a-z]+)$', reste)
            if m:
                typ, cible, severite = m.groups()
                alertes.append({'type': typ, 'severity': severite, 'target_entity_id': cible,
                                'evidence': [preuves[i] for i in src.split('+') if i in preuves]})
        elif ' → ' in ligne:
            src, reste = ligne.split(' → ', 1)
            m = re.match(r'^([a-z_]+)(?:\.([a-z_]+))?(?:@(ent_\d+))?:(.)(~?):([a-z]+)$', reste)
            if m:
                famille, attribut, cible, signe, implicite, intensite = m.groups()
                aspect = {'family': famille, 'target_entity_id': cible,
                          'sentiment': SIGNE_INV.get(signe, 'negatif'),
                          'intensity': intensite, 'implicit': implicite == '~',
                          'evidence': [preuves[i] for i in src.split('+') if i in preuves]}
                if attribut:
                    aspect['attribute'] = attribut
                aspects.append(aspect)
        elif ligne.startswith('∴'):
            intents = [i for i in ligne[1:].strip().split(',') if i]

    annotation = {**scan, 'monitoring_target': monitoring_target,
                  'entities': entites, 'sentiment': sentiment, 'intents': intents,
                  'aspects': aspects, 'alerts': alertes, 'schema_version': version}
    for bloc in [sentiment] + aspects + alertes:
        if bloc:
            bloc['evidence'] = resoudre_offsets(bloc.get('evidence'), texte)
    for e in entites:
        resoudre_entite(e, texte)
    annotation['actionability'] = deriver_actionability(annotation)
    return annotation


def comparer(origine: dict, reconstruite: dict) -> list[str]:
    """Champs qui different. Un format sans perte n'en produit aucun."""
    ecarts = []
    for champ in ('is_exploitable', 'non_exploitable_reason', 'business_relevance',
                  'author_role', 'requires_parent_context'):
        if origine.get(champ) != reconstruite.get(champ):
            ecarts.append(champ)
    for champ in ('dominant', 'detected', 'code_switching', 'scripts'):
        if (origine.get('language') or {}).get(champ) != \
           (reconstruite.get('language') or {}).get(champ):
            ecarts.append(f'language.{champ}')
    for champ in ('label', 'intensity', 'emotion', 'sarcasm', 'target_entity_ids'):
        if (origine.get('sentiment') or {}).get(champ) != \
           (reconstruite.get('sentiment') or {}).get(champ):
            ecarts.append(f'sentiment.{champ}')
    if sorted(origine.get('intents') or []) != sorted(reconstruite.get('intents') or []):
        ecarts.append('intents')
    for nom, cles in (('aspects', ('family', 'attribute', 'target_entity_id', 'sentiment',
                                   'intensity', 'implicit')),
                      ('alerts', ('type', 'severity', 'target_entity_id')),
                      ('entities', ('id', 'type', 'name', 'source'))):
        a = [tuple(x.get(c) for c in cles) for x in origine.get(nom) or []]
        b = [tuple(x.get(c) for c in cles) for x in reconstruite.get(nom) or []]
        if sorted(map(str, a)) != sorted(map(str, b)):
            ecarts.append(nom)
    return ecarts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--annotations', action='append', required=True)
    ap.add_argument('--texts', action='append', required=True)
    ap.add_argument('--limit', type=int, default=None)
    args = ap.parse_args()

    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained('Qwen/Qwen3-0.6B')
    schema = json.loads((ROOT / 'docs/slm_v2/business_comment_annotation_v0.4.schema.json')
                        .read_text(encoding='utf-8'))
    version = schema['properties']['schema_version']['const']

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
    ids = [i for i in annotations if i in entrees][:args.limit]

    ecarts, tokens, parfaits = Counter(), [], 0
    for rid in ids:
        texte = entrees[rid]['text']
        cible = entrees[rid].get('monitoring_target')
        origine = {k: v for k, v in annotations[rid].items()
                   if k not in ('record_id', 'annotator', 'notes', 'lecture_fr')}
        for bloc in ([origine.get('sentiment') or {}] + (origine.get('aspects') or [])
                     + (origine.get('alerts') or [])):
            if 'evidence' in bloc:
                bloc['evidence'] = resoudre_offsets(bloc['evidence'], texte)
        for e in origine.get('entities') or []:
            resoudre_entite(e, texte)

        fil = encoder(origine, texte)
        tokens.append(len(tok.encode(fil)))
        diff = comparer(origine, decoder(fil, texte, cible, version))
        parfaits += not diff
        for d in diff:
            ecarts[d] += 1

    import statistics as st
    print(f'annotations testees : {len(ids)}')
    print(f'aller-retour exact  : {parfaits} = {parfaits / len(ids):.2%}')
    if ecarts:
        print('champs perdus :')
        for champ, n in ecarts.most_common(12):
            print(f'  {n:6d}  {champ}')
    print(f'\nsortie du modele : mediane {int(st.median(tokens))}, '
          f'p95 {sorted(tokens)[int(.95 * len(tokens))]}, max {max(tokens)} tokens')
    print(f'  budget benchmark : 256   ·   tenu par '
          f'{sum(t <= 256 for t in tokens) / len(tokens):.0%} des exemples')
    return 0 if parfaits == len(ids) else 1


if __name__ == '__main__':
    raise SystemExit(main())
