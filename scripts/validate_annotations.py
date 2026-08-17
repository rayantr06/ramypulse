#!/usr/bin/env python3
"""Valide un lot d'annotations contre le contrat courant (V0.4).

Les controles integres a `annotate_vertex.py` sont bon marche et locaux : ils
verifient qu'une preuve figure dans le texte, qu'un aspect n'est pas neutre. Ils
ne verifient PAS l'appartenance aux vocabulaires fermes — et le pilote Maps a
montre que cela manque : `ethique_impact`, qui est une famille d'aspect, s'est
retrouve utilise comme type d'alerte, valeur que l'enumeration n'admet pas.

Ce script fait ce que le controle en ligne ne peut pas faire a moindre cout :
il applique le schema complet, apres avoir reconstitue ce que le pipeline
ajoute — offsets resolus depuis les extraits litteraux, `actionability` derivee.

Usage :
  python scripts/validate_annotations.py --input <dir output> --texts <dir input>
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / 'docs/slm_v2/business_comment_annotation_v0.4.schema.json'
#: Champs de travail, absents du contrat : le schema refuse tout ajout.
HORS_CONTRAT = ('record_id', 'annotator', 'notes', 'lecture_fr')
SEV = {'faible': 1, 'moyenne': 2, 'elevee': 3}
SEV_INV = {v: k for k, v in SEV.items()}
QUEUE = {
    'produit_service': 'produit', 'prix_valeur': 'pricing',
    'disponibilite_acces': 'operations', 'experience_client': 'service_client',
    'service_client_sav': 'service_client', 'livraison_logistique': 'logistique',
    'digital_technologie': 'digital', 'communication_information': 'communication',
    'confiance_reputation': 'communication', 'operations_processus': 'operations',
    'emploi_management': 'rh', 'securite_conformite': 'juridique_conformite',
    'ethique_impact': 'direction', 'marche_innovation': 'direction',
    'infrastructure_service_public': 'service_public',
}


def resoudre_offsets(evidence, texte: str) -> list:
    """Transforme les extraits litteraux en objets `{text, start, end}`.

    Le modele ne calcule aucun offset : c'est le pipeline qui s'en charge, et
    c'est ce choix qui a supprime toutes les erreurs mecaniques de position.
    """
    sortie = []
    if isinstance(evidence, str):
        evidence = [evidence] if evidence.strip() else []
    for element in evidence or []:
        if isinstance(element, dict):
            sortie.append(element)
            continue
        if not isinstance(element, str) or not element.strip():
            continue
        debut = texte.find(element)
        if debut < 0:
            continue
        sortie.append({'text': element, 'start': debut, 'end': debut + len(element)})
    return sortie


def resoudre_entite(entite: dict, texte: str) -> None:
    """Resout `start`/`end` d'une entite depuis sa `mention`.

    Le schema exige des entiers des lors que `source` vaut `texte`, et `null`
    quand elle vaut `contexte`. Le modele, lui, ne calcule aucun offset : c'est
    ce partage qui a supprime toutes les erreurs mecaniques de position. La
    resolution appartient donc ici, comme pour les preuves.

    Une mention introuvable dans le texte n'est pas reparee : `source` bascule
    sur `contexte`, ce qui est la verite — l'entite n'est pas litteralement la.
    """
    if entite.get('source') == 'contexte':
        entite['mention'] = entite['start'] = entite['end'] = None
        return
    mention = entite.get('mention')
    debut = texte.find(mention) if isinstance(mention, str) and mention else -1
    if debut < 0:
        entite['source'] = 'contexte'
        entite['mention'] = entite['start'] = entite['end'] = None
        return
    entite['start'], entite['end'] = debut, debut + len(mention)


def nettoyer_attribut(aspect: dict, attendus: dict) -> bool:
    """Retire un `attribute` hors de la liste autorisee pour sa famille.

    Le schema le decrit lui-meme comme un « detail optionnel non evalue par les
    portes de qualite », et sa liste change avec `family` — quinze enums
    conditionnelles. Jeter une annotation entiere pour un detail facultatif et
    non score serait disproportionne : 25 des 32 rejets du holdout venaient de la.
    Le retrait est compte, pas silencieux.
    """
    valeur = aspect.get('attribute')
    if valeur is None:
        return False
    autorises = attendus.get(aspect.get('family'))
    if autorises is None or valeur in autorises:
        return False
    aspect.pop('attribute')
    return True


def attributs_autorises(schema: dict) -> dict:
    table = {}
    for regle in schema['$defs']['aspect'].get('allOf', []):
        famille = (((regle.get('if') or {}).get('properties') or {})
                   .get('family') or {}).get('const')
        valeurs = (((regle.get('then') or {}).get('properties') or {})
                   .get('attribute') or {}).get('enum')
        if famille and valeurs:
            table[famille] = set(valeurs)
    return table


def deriver_actionability(ligne: dict) -> dict:
    """`priority` est derivee, jamais annotee : c'est ce qui l'a fait passer de
    kappa 0,306 a 0,907. Deux annotateurs ne s'accordaient pas dessus, mais
    s'accordaient sur les champs dont elle se calcule."""
    alertes, aspects = ligne.get('alerts') or [], ligne.get('aspects') or []
    org = (ligne.get('monitoring_target') or {}).get('scope') == 'organisation'
    negatifs = [a for a in aspects if a.get('sentiment') == 'negatif']
    if alertes and org:
        priorite = SEV_INV[max(SEV.get(a.get('severity'), 1) for a in alertes)]
    elif org and any(a.get('intensity') == 'forte' for a in negatifs):
        priorite = 'moyenne'
    else:
        priorite = 'faible'
    dominant = negatifs[0] if negatifs else (aspects[0] if aspects else None)
    return {
        'actionable': bool(org and (alertes or negatifs)),
        'queue': QUEUE.get((dominant or {}).get('family'), 'aucune') if org else 'aucune',
        'priority': priorite,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', required=True, help='dossier des .out.jsonl')
    ap.add_argument('--texts', action='append', required=True, help='dossier des textes source')
    ap.add_argument('--out', default=None, help='fichier des lignes invalides')
    args = ap.parse_args()

    import jsonschema

    schema = json.loads(SCHEMA_PATH.read_text(encoding='utf-8'))
    version = schema['properties']['schema_version']['const']
    valideur = jsonschema.Draft202012Validator(schema)
    attendus = attributs_autorises(schema)
    attributs_retires = 0

    textes = {}
    for dossier in args.texts:
        chemin = Path(dossier)
        for fichier in (sorted(chemin.glob('*.jsonl')) if chemin.is_dir() else [chemin]):
            for ligne in fichier.read_text(encoding='utf-8').splitlines():
                if ligne.strip():
                    r = json.loads(ligne)
                    textes[r['record_id']] = r['text']

    total = valides = 0
    motifs: Counter[str] = Counter()
    invalides = []
    for fichier in sorted(Path(args.input).glob('*.out.jsonl')):
        for ligne in fichier.read_text(encoding='utf-8').splitlines():
            if not ligne.strip():
                continue
            brut = json.loads(ligne)
            total += 1
            rid = brut.get('record_id')
            texte = textes.get(rid, '')
            normalise = {k: v for k, v in brut.items() if k not in HORS_CONTRAT}
            normalise['schema_version'] = version
            for bloc in ([normalise.get('sentiment') or {}]
                         + (normalise.get('aspects') or [])
                         + (normalise.get('alerts') or [])):
                if 'evidence' in bloc:
                    bloc['evidence'] = resoudre_offsets(bloc['evidence'], texte)
            for entite in normalise.get('entities') or []:
                resoudre_entite(entite, texte)
            for aspect in normalise.get('aspects') or []:
                attributs_retires += nettoyer_attribut(aspect, attendus)
            normalise['actionability'] = deriver_actionability(normalise)

            erreurs = sorted(valideur.iter_errors(normalise), key=lambda e: list(e.path))
            if not erreurs:
                valides += 1
                continue
            for err in erreurs[:3]:
                chemin_champ = '.'.join(str(p) for p in err.path if not isinstance(p, int))
                motifs[f'{chemin_champ or "(racine)"} — {err.validator}'] += 1
            invalides.append({'record_id': rid,
                              'erreurs': [e.message[:160] for e in erreurs[:3]]})

    print(f'annotations   : {total}')
    print(f'valides       : {valides} = {valides / max(total, 1):.1%}')
    print(f'invalides     : {total - valides}')
    if attributs_retires:
        print(f'attributs facultatifs retires (hors liste de leur famille) : {attributs_retires}')
    for motif, n in motifs.most_common(15):
        print(f'  {n:5d}  {motif}')
    if invalides[:3]:
        print('\nexemples :')
        for x in invalides[:3]:
            print(f'  [{x["record_id"]}] {x["erreurs"][0]}')
    if args.out and invalides:
        Path(args.out).write_text(
            ''.join(json.dumps(x, ensure_ascii=False) + '\n' for x in invalides),
            encoding='utf-8')
        print(f'\ninvalides ecrits : {args.out}')
    return 1 if invalides else 0


if __name__ == '__main__':
    raise SystemExit(main())
