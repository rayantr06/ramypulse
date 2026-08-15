#!/usr/bin/env python3
"""Projection deterministe d'une annotation vers sa trace canonique, et compilation
vers la trace compacte d'entrainement.

Ces deux etapes ne coutent aucun appel de modele. C'est voulu : l'audit du
29 juillet prescrit que « le professeur ne doit pas regenerer ce qui peut etre
derive sans ambiguite ». Tout ce qui se lit dans l'annotation acceptee — la carte
de preuves, les decisions explicites, la complexite, les liens preuve-decision —
est calcule ici. Le professeur ne complete ensuite que ce qui demande un
jugement : regles de desambiguisation, portee de negation ou de sarcasme, liens
implicites, incertitudes reellement considerees.

Deux representations, conformement a la decision inscrite :

- **trace canonique** : objet JSON valide contre `business_decision_trace_v0.1`,
  destine a l'audit, a la regeneration et au controle. Jamais envoye au modele
  de production.
- **trace compacte** : compilee par une fonction deterministe, c'est elle qui
  entre dans l'entrainement, sous la forme `<think> ... </think>` + JSON.

La notation active se limite a deux marqueurs, `→` et `∴`. Le reste de la
grammaire Baguettotron est explicitement reporte : la confiance et la
verification sont produites par les validateurs, jamais auto-declarees par
l'eleve, et l'entropie simulee n'a pas de sens pour une extraction deterministe.

Usage :
  python scripts/trace_projection.py --input <dir annotations> --texts <dir source> \
                                     --output <dir traces> [--tokenizer <chemin>]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from validate_annotations import (  # noqa: E402
    QUEUE, deriver_actionability, resoudre_entite, resoudre_offsets,
)

TRACE_SCHEMA = ROOT / 'docs/slm_v2/business_decision_trace_v0.2.schema.json'
NOTATION = ROOT / 'docs/slm_v2/reasoning_notation_v0.1.json'
PROMPT_VERSION = 'projection_v0.1'

#: Plafonds par niveau. Ce sont des plafonds, pas des objectifs : un cas simple
#: ne doit pas etre allonge artificiellement.
#:
#: L'audit de juillet proposait 64 / 128 / 192, qu'il qualifiait lui-meme de
#: « niveaux initiaux » — aucun corpus n'existait alors pour les mesurer. Sur les
#: 594 traces du holdout Maps, tokenizer Qwen3-0.6B, la mediane observee est de
#: 124 / 192 / 259 : les plafonds etaient depasses par 96 %, 90 % et 86 % des
#: traces. La compression disponible ne rend que 11 % — retirer l'attribut, non
#: evalue par les portes, et l'intensite d'aspect. Le decalage est structurel :
#: un avis Maps porte 3,8 preuves et une douzaine de lignes de decision.
#:
#: Les valeurs sont donc reprises au 75e centile mesure, arrondi. Elles couvrent
#: environ 80 % des cas et laissent la queue a comprimer, ce qu'un plafond doit
#: faire. Les fixer a la mediane ne contraindrait plus rien.
PLAFONDS = {'simple': 160, 'medium': 256, 'complex': 320}
#: Bornes de score, section 7 de l'audit.
NIVEAUX = ((1, 'simple'), (3, 'medium'))
#: Le marqueur `→` est plafonne a 12 par trace par le manifeste de notation.
MAX_FLECHES = 12

SIGNE = {'positif': '+', 'negatif': '-', 'mixte': '±', 'neutre': '0'}


def complexite(annotation: dict) -> dict:
    """Score de complexite, section 7 de l'audit. Il fixe le plafond de tokens."""
    facteurs = []
    langue = annotation.get('language') or {}
    aspects = annotation.get('aspects') or []
    alertes = annotation.get('alerts') or []
    sentiment = annotation.get('sentiment') or {}

    if not annotation.get('is_exploitable'):
        facteurs.append('non_exploitable')
    if langue.get('code_switching'):
        facteurs.append('code_switching')
    if len(langue.get('scripts') or []) > 1:
        facteurs.append('multi_script')
    if len(annotation.get('entities') or []) > 1:
        facteurs.append('multiple_entities')
    if len({a.get('target_entity_id') for a in aspects if a.get('target_entity_id')}) > 1:
        facteurs.append('multiple_targets')
    if len(aspects) >= 3:
        facteurs.append('multiple_aspects')
    if sentiment.get('label') == 'mixte':
        facteurs.append('mixed_sentiment')
    if any(a.get('implicit') for a in aspects):
        facteurs.append('implicit_aspect')
    if sentiment.get('sarcasm'):
        facteurs.append('sarcasm')
    if alertes:
        facteurs.append('alert')
    if any(a.get('severity') in ('elevee', 'critique') for a in alertes):
        facteurs.append('high_severity_alert')   # compte double

    score = len(facteurs) + sum(f == 'high_severity_alert' for f in facteurs)
    niveau = next((n for borne, n in NIVEAUX if score <= borne), 'complex')
    return {'level': niveau, 'score': score, 'factors': facteurs,
            'max_trace_tokens': PLAFONDS[niveau], 'observed_trace_tokens': 0}


def regle_sentiment(sentiment: dict) -> str:
    """Regle de decision impliquee par l'etiquette elle-meme."""
    if sentiment.get('sarcasm'):
        return 'sarcasme_inverse'
    return {'mixte': 'polarites_mixtes', 'neutre': 'neutre_sans_opinion'}.get(
        sentiment.get('label'), 'polarite_explicite')


def regle_aspect(aspect: dict) -> str:
    """Chaque bloc a sa propre enumeration de regles : celle des aspects n'est
    pas celle du sentiment. La projection pose le cas par defaut."""
    if aspect.get('sentiment') == 'mixte':
        return 'polarite_mixte'
    return 'inference_contextuelle' if aspect.get('implicit') else 'mention_directe'


def declencheur_alerte(alerte: dict) -> str:
    return ('incident_explicite' if alerte.get('evidence')
            else 'inference_prudente')


def regle_action(annotation: dict, action: dict) -> str:
    """Reflete la derivation D2/D3 : l'alerte prime, puis l'aspect negatif."""
    if not action.get('actionable'):
        return 'aucune_action'
    if annotation.get('alerts'):
        return 'alerte_prioritaire'
    return 'aspect_prioritaire'


def carte_de_preuves(annotation: dict, texte: str) -> tuple[list, dict]:
    """Deduplique les preuves et leur attribue un identifiant stable.

    Une meme portion de texte peut appuyer plusieurs decisions ; la carte
    l'enregistre une fois et note tous ses roles. C'est ce qui permet ensuite
    d'ecrire `ev1+ev2 → sentiment:mixte` au lieu de repeter les extraits.
    """
    carte: dict[tuple, dict] = {}
    index: dict[int, list] = {}

    def ajouter(bloc: dict, role: str, cle_bloc):
        ids = []
        for e in resoudre_offsets(bloc.get('evidence'), texte):
            cle = (e['start'], e['end'])
            if cle not in carte:
                carte[cle] = {'id': f'ev_{len(carte) + 1}', 'text': e['text'],
                              'start': e['start'], 'end': e['end'], 'roles': []}
            if role not in carte[cle]['roles']:
                carte[cle]['roles'].append(role)
            ids.append(carte[cle]['id'])
        index.setdefault(id(cle_bloc), []).extend(ids)
        return ids

    ajouter(annotation.get('sentiment') or {}, 'sentiment', annotation.get('sentiment'))
    for a in annotation.get('aspects') or []:
        ajouter(a, 'aspect', a)
    for a in annotation.get('alerts') or []:
        ajouter(a, 'alert', a)

    preuves = sorted(carte.values(), key=lambda e: e['start'])
    return preuves, index


def projeter(annotation: dict, texte: str) -> dict:
    """Construit la trace canonique a partir de ce qui est deja dans l'annotation."""
    preuves, index = carte_de_preuves(annotation, texte)
    par_bloc = lambda bloc: index.get(id(bloc), [])          # noqa: E731

    langue = annotation.get('language') or {}
    sentiment = annotation.get('sentiment') or {}
    entites = annotation.get('entities') or []
    for e in entites:
        resoudre_entite(e, texte)

    actionability = deriver_actionability(annotation)
    decisions = {
        'entities': [{'entity_id': e['id'], 'type': e['type'], 'source': e['source'],
                      'evidence_ids': [], 'rule': ('mention_explicite'
                                                   if e['source'] == 'texte'
                                                   else 'contexte_fourni')}
                     for e in entites],
        'overall_sentiment': {
            'label': sentiment.get('label'), 'intensity': sentiment.get('intensity'),
            'emotion': sentiment.get('emotion'), 'sarcasm': bool(sentiment.get('sarcasm')),
            'evidence_ids': par_bloc(annotation.get('sentiment')),
            # `rule` est enumere. La projection pose ce que le label implique ;
            # le professeur corrigera s'il y a negation, sarcasme ou inference.
            'rule': regle_sentiment(sentiment)},
        'intents': [{'label': i, 'mode': 'explicite', 'evidence_ids': []}
                    for i in annotation.get('intents') or []],
        'aspects': [{'family': a['family'], 'target_entity_id': a.get('target_entity_id'),
                     'sentiment': a['sentiment'], 'intensity': a['intensity'],
                     'implicit': bool(a.get('implicit')), 'evidence_ids': par_bloc(a),
                     'rule': regle_aspect(a),
                     **({'attribute': a['attribute']} if a.get('attribute') else {})}
                    for a in annotation.get('aspects') or []],
        'alerts': [{'type': a['type'], 'severity': a['severity'],
                    'target_entity_id': a.get('target_entity_id'),
                    'evidence_ids': par_bloc(a), 'trigger': declencheur_alerte(a)}
                   for a in annotation.get('alerts') or []],
        'actionability': {**actionability, 'evidence_ids': [],
                          'rule': regle_action(annotation, actionability)},
    }

    empreinte = lambda s: hashlib.sha256(s.encode('utf-8')).hexdigest()   # noqa: E731
    return {
        'trace_version': 'business_decision_trace_v0.2',
        'complexity': complexite(annotation),
        'scan': {
            'is_exploitable': annotation.get('is_exploitable'),
            'non_exploitable_reason': annotation.get('non_exploitable_reason'),
            'business_relevance': annotation.get('business_relevance'),
            'language_dominant': langue.get('dominant'),
            'code_switching': bool(langue.get('code_switching')),
            'scripts': langue.get('scripts') or [],
            'quality_flags': [],
        },
        'evidence_map': preuves,
        'decisions': decisions,
        # Le professeur les remplira : la projection ne peut pas savoir ce qui a
        # ete hesite.
        'uncertainties': [],
        'provenance': {
            'method': 'deterministic_projection', 'teacher_model': None,
            'critic_model': None, 'prompt_version': PROMPT_VERSION,
            'text_sha256': empreinte(texte),
            'annotation_sha256': empreinte(json.dumps(annotation, sort_keys=True,
                                                      ensure_ascii=False)),
            'generated_at': '',
        },
        'validation': {'schema_valid': False, 'all_evidence_exact': False,
                       'trace_annotation_consistent': False, 'no_new_labels': False,
                       'no_unsupported_facts': False, 'within_token_budget': False,
                       'critic_passed': False},
    }


def compiler_compacte(trace: dict) -> str:
    """Compile la trace canonique vers la forme dense d'entrainement.

    L'ordre suit `compiler_order` du manifeste de notation. Seuls `→` et `∴` sont
    employes : les autres marqueurs de la grammaire Baguettotron sont reportes,
    et la confiance comme la verification appartiennent aux validateurs.
    """
    scan, dec = trace['scan'], trace['decisions']
    lignes = []
    etat = 'exploitable' if scan['is_exploitable'] else f"non:{scan['non_exploitable_reason']}"
    lignes.append(f"scan → {etat},{scan['business_relevance']},{scan['language_dominant']}")

    # La carte de preuves vient en premier, chaque extrait cite UNE fois. Les
    # decisions le referencent ensuite par identifiant. C'est l'ordre prescrit
    # par `compiler_order`, et c'est ce qui evite de repeter un long extrait
    # francais a chaque decision qu'il appuie.
    #
    # Aucun offset n'apparait ici, contrairement a l'exemple de l'audit. Le
    # projet impose depuis l'origine que le modele ne calcule aucune position :
    # c'est ce partage qui a supprime toutes les erreurs mecaniques. Faire
    # ecrire `[181:230]` a l'eleve les reintroduirait.
    for preuve in trace['evidence_map']:
        lignes.append(f'{preuve["id"]}="{preuve["text"]}"')

    for entite in dec['entities']:
        lignes.append(f"{entite['entity_id']}:{entite['type']} → source:{entite['source']}")

    for aspect in dec['aspects']:
        ids = '+'.join(aspect.get('evidence_ids') or []) or 'ctx'
        detail = f".{aspect['attribute']}" if aspect.get('attribute') else ''
        cible = f"@{aspect['target_entity_id']}" if aspect.get('target_entity_id') else ''
        lignes.append(f"{ids} → {aspect['family']}{detail}{cible}"
                      f":{SIGNE[aspect['sentiment']]}:{aspect['intensity']}")

    sentiment = dec['overall_sentiment']
    origine = '+'.join(sentiment.get('evidence_ids') or []) or 'scan'
    sarcasme = ',sarcasme' if sentiment.get('sarcasm') else ''
    lignes.append(f"{origine} → sentiment:{sentiment['label']}"
                  f":{sentiment['intensity']}:{sentiment['emotion']}{sarcasme}")

    for alerte in dec['alerts']:
        ids = '+'.join(alerte.get('evidence_ids') or []) or 'ctx'
        lignes.append(f"{ids} → alerte:{alerte['type']}:{alerte['severity']}")

    for incertitude in trace.get('uncertainties') or []:
        if incertitude.get('status') == 'unresolved':
            lignes.append(f"? {incertitude['field']}:{incertitude['issue'][:40]}")

    # Le manifeste plafonne `→` a 12. Au-dela, les aspects les moins intenses
    # sont retires de la trace compacte — ils restent dans la canonique.
    fleches = [l for l in lignes if '→' in l]
    if len(fleches) > MAX_FLECHES:
        a_retirer = set(fleches[MAX_FLECHES - 1:-1])
        lignes = [l for l in lignes if l not in a_retirer]

    action = dec['actionability']
    intents = ','.join(i['label'] for i in dec['intents']) or 'aucun'
    alertes = ','.join(f"{a['type']}/{a['severity']}" for a in dec['alerts']) or 'none'
    lignes.append(f"∴ intents:{intents}; alerts:{alertes}; "
                  f"action:{action['queue']}/{action['priority']}")
    return '<think>\n' + '\n'.join(lignes) + '\n</think>'


def compter_tokens(texte: str, tokenizer=None) -> tuple[int, bool]:
    """Retourne (nombre, mesure_reelle). Sans tokenizer, l'estimation est
    grossiere et doit etre signalee comme telle plutot que presentee comme
    une mesure."""
    if tokenizer is not None:
        return len(tokenizer.encode(texte)), True
    return max(1, len(texte) // 3), False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', required=True)
    ap.add_argument('--texts', action='append', required=True)
    ap.add_argument('--output', required=True)
    ap.add_argument('--tokenizer', default=None,
                    help='chemin d un tokenizer HuggingFace pour compter reellement')
    ap.add_argument('--limit', type=int, default=None)
    args = ap.parse_args()

    import jsonschema
    schema = json.loads(TRACE_SCHEMA.read_text(encoding='utf-8'))
    valideur = jsonschema.Draft202012Validator(schema)

    tokenizer = None
    if args.tokenizer:
        from transformers import AutoTokenizer
        tokenizer = AutoTokenizer.from_pretrained(args.tokenizer)

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
    niveaux, depassements, invalides, total = Counter(), Counter(), 0, 0
    mesure_reelle = True
    exemples = []

    for lot in sorted(Path(args.input).glob('*.out.jsonl')):
        lignes = []
        for ligne in lot.read_text(encoding='utf-8').splitlines():
            if not ligne.strip():
                continue
            annotation = json.loads(ligne)
            rid = annotation['record_id']
            if rid not in textes:
                continue
            if args.limit and total >= args.limit:
                break
            texte = textes[rid]
            propre = {k: v for k, v in annotation.items()
                      if k not in ('record_id', 'annotator', 'notes', 'lecture_fr')}
            trace = projeter(propre, texte)
            compacte = compiler_compacte(trace)
            n, reelle = compter_tokens(compacte, tokenizer)
            mesure_reelle &= reelle
            trace['complexity']['observed_trace_tokens'] = n
            plafond = trace['complexity']['max_trace_tokens']
            trace['validation']['within_token_budget'] = n <= plafond
            trace['validation']['all_evidence_exact'] = all(
                e['text'] == texte[e['start']:e['end']] for e in trace['evidence_map'])

            erreurs = list(valideur.iter_errors(trace))
            trace['validation']['schema_valid'] = not erreurs
            invalides += bool(erreurs)
            if erreurs and len(exemples) < 3:
                exemples.append((rid, erreurs[0].message[:150]))
            niveaux[trace['complexity']['level']] += 1
            depassements[trace['complexity']['level']] += n > plafond
            total += 1
            lignes.append({'record_id': rid, 'decision_trace': trace,
                           'compact_trace': compacte})
        if lignes:
            (sortie / lot.name.replace('.out.jsonl', '.trace.jsonl')).write_text(
                ''.join(json.dumps(x, ensure_ascii=False) + '\n' for x in lignes),
                encoding='utf-8')
        if args.limit and total >= args.limit:
            break

    print(f'traces projetees : {total}')
    print(f'invalides au schema : {invalides}')
    for rid, msg in exemples:
        print(f'  [{rid}] {msg}')
    print(f"\ncomptage de tokens : {'reel' if mesure_reelle else 'ESTIME (pas de tokenizer)'}")
    print(f"{'niveau':10s} {'n':>6s} {'plafond':>8s} {'depassements':>13s}")
    for niveau in ('simple', 'medium', 'complex'):
        n = niveaux[niveau]
        if n:
            print(f'{niveau:10s} {n:6d} {PLAFONDS[niveau]:8d} '
                  f'{depassements[niveau]:6d} = {depassements[niveau] / n:5.1%}')
    return 1 if invalides else 0


if __name__ == '__main__':
    raise SystemExit(main())
