#!/usr/bin/env python3
"""Consolide le gold V0.3 à partir de tout ce qui a été mesuré.

Chaque item reçoit un palier de confiance explicite, du plus fiable au moins :

  repasse_R1        étape de traduction imposée, validée par 4 critères
  valide_humain     relu et confirmé par le propriétaire du projet
  accord_A3_C       deux annotateurs indépendants s'accordent sur les 5 champs
                    critiques, taux d'acceptation humain mesuré à 90 %
  arbitrage_requis  désaccord non résolu — EXCLU du gold utilisable

Le palier est conservé dans chaque ligne. Un consommateur du jeu peut ainsi
choisir son niveau d'exigence au lieu de recevoir une confiance uniforme
qu'aucune mesure ne soutient.

Usage : python scripts/build_gold_v03.py
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
CP = ROOT / 'data/processed/slm_v2_gold/campaign_v0.2'
RP = ROOT / 'data/processed/slm_v2_gold/arabizi_repass_v0.3'
HV = ROOT / 'data/processed/slm_v2_gold/human_validation_v0.3'
OUT = ROOT / 'data/processed/slm_v2_gold/gold_v0.3'
SCHEMA = ROOT / 'docs/slm_v2/business_comment_annotation_v0.3.schema.json'

CRIT = ['is_exploitable', 'business_relevance', 'sentiment.label', 'aspects', 'alerts']

# Corrections explicites issues de la relecture humaine du 2026-07-30, pour les
# items que la repasse n'a pas couverts. Appliquer un verdict humain connu vaut
# mieux que laisser une erreur documentée entrer dans le gold.
CORRECTIONS_HUMAINES = {
    'v02_0212': {'sentiment.label': 'neutre', 'aspects': [],
                 'motif': "formule d'espoir religieuse, pas un eloge de la marque"},
}


def load(d: Path) -> dict:
    o = {}
    for p in sorted(d.glob('batch_*.out.jsonl')):
        for line in p.read_text(encoding='utf-8').splitlines():
            if line.strip():
                r = json.loads(line)
                o[r['record_id']] = r
    return o


def crit(r: dict, f: str):
    if f == 'sentiment.label':
        return r['sentiment']['label']
    if f == 'aspects':
        return tuple(sorted((a['family'], a['sentiment']) for a in r['aspects']))
    if f == 'alerts':
        return tuple(sorted((a['type'], a['severity']) for a in r['alerts']))
    return r[f]


def human_verdicts() -> dict:
    key = {x['n']: x for x in json.loads((HV / '_cle_ne_pas_ouvrir.json').read_text(encoding='utf-8'))}
    md = (HV / 'REVUE_HUMAINE.md').read_text(encoding='utf-8')
    blocks = re.split(r'^## (\d+)\. ', md, flags=re.M)[1:]
    out = {}
    for i in range(0, len(blocks), 2):
        n, body = int(blocks[i]), blocks[i + 1]
        for lab, kw in (('correcte', 'correcte'), ('nuance', 'acceptable'),
                        ('incorrecte', 'incorrecte')):
            for line in body.splitlines():
                st = line.strip()
                if not st.startswith('-'):
                    continue
                low = st.lower()
                idx = low.find(kw)
                if idx < 0:
                    continue
                if 'x' in low[1:idx]:
                    out[key[n]['record_id']] = lab
                break
    return out


def offsets(ev: list, text: str) -> list:
    out, cur = [], 0
    for e in ev:
        s = text.find(e, cur)
        if s < 0:
            s = text.find(e)
        if s < 0:
            continue
        cur = s + len(e)
        out.append({'text': e, 'start': s, 'end': s + len(e)})
    return out


QUEUE = {'produit_service': 'produit', 'prix_valeur': 'pricing',
         'disponibilite_acces': 'logistique', 'experience_client': 'service_client',
         'service_client_sav': 'service_client', 'livraison_logistique': 'logistique',
         'digital_technologie': 'digital', 'communication_information': 'communication',
         'confiance_reputation': 'communication', 'operations_processus': 'operations',
         'emploi_management': 'rh', 'securite_conformite': 'securite_qualite',
         'ethique_impact': 'direction', 'marche_innovation': 'direction',
         'infrastructure_service_public': 'service_public'}
SEV = {'faible': 1, 'moyenne': 2, 'elevee': 3}
SEVI = {1: 'faible', 2: 'moyenne', 3: 'elevee'}


def normalise(row: dict, text: str, famattrs: dict) -> dict:
    o = {k: v for k, v in row.items()
         if k not in ('record_id', 'annotator', 'notes', 'lecture_fr')}
    o['schema_version'] = '0.3.0'
    s = dict(o['sentiment'])
    s['evidence'] = offsets(s.get('evidence') or [], text)
    o['sentiment'] = s
    for key in ('aspects', 'alerts'):
        items = []
        for it in o.get(key) or []:
            it = dict(it)
            it['evidence'] = offsets(it.get('evidence') or [], text)
            if key == 'alerts' and it.get('severity') == 'critique':
                it['severity'] = 'elevee'
            if key == 'aspects' and it.get('attribute') is not None:
                if it['attribute'] not in famattrs.get(it.get('family'), set()):
                    it.pop('attribute')
            items.append(it)
        o[key] = items
    for e in o.get('entities') or []:
        if e.get('source') == 'texte' and isinstance(e.get('mention'), str):
            i = text.find(e['mention'])
            e['start'], e['end'] = (i, i + len(e['mention'])) if i >= 0 else (None, None)
            if i < 0:
                e['source'], e['mention'] = 'contexte', None
        else:
            e['mention'] = e['start'] = e['end'] = None
    org = o['monitoring_target']['scope'] == 'organisation'
    alerts, asp = o['alerts'], o['aspects']
    if alerts and org:
        prio = SEVI[max(SEV[a['severity']] for a in alerts)]
    elif org and any(a['sentiment'] == 'negatif' and a['intensity'] == 'forte' for a in asp):
        prio = 'moyenne'
    else:
        prio = 'faible'
    dom = sorted(asp, key=lambda a: ({'negatif': 0, 'mixte': 1, 'positif': 2}.get(a['sentiment'], 9),
                                     {'forte': 0, 'moyenne': 1, 'faible': 2}.get(a['intensity'], 9)))
    dom = dom[0] if dom else None
    actionable = bool(org and (alerts or (dom and dom['sentiment'] in ('negatif', 'mixte'))))
    o['actionability'] = {'actionable': actionable,
                          'queue': QUEUE.get(dom['family'], 'aucune') if (dom and actionable) else 'aucune',
                          'priority': prio if actionable else 'faible'}
    return o


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    schema = json.loads(SCHEMA.read_text(encoding='utf-8'))
    famattrs = {}
    for r in schema['$defs']['aspect'].get('allOf', []):
        f = r.get('if', {}).get('properties', {}).get('family', {}).get('const')
        a = r.get('then', {}).get('properties', {}).get('attribute', {}).get('enum')
        if f and a:
            famattrs[f] = set(a)
    validator = Draft202012Validator(schema)

    A, C, R = load(CP / 'output_a'), load(CP / 'output_c'), load(RP / 'output')
    items = {r['record_id']: r for p in sorted((CP / 'input').glob('batch_*.jsonl'))
             for r in (json.loads(l) for l in p.read_text(encoding='utf-8').splitlines() if l.strip())}
    hv = human_verdicts()
    ids = sorted(set(A) & set(C))

    gold, pending, invalid = [], [], []
    for i in ids:
        agree = all(crit(A[i], f) == crit(C[i], f) for f in CRIT)
        if i in R:
            src, tier = R[i], 'repasse_R1'
        elif hv.get(i) in ('correcte', 'nuance'):
            src, tier = A[i], 'valide_humain'
        elif agree:
            src, tier = A[i], 'accord_A3_C'
        else:
            pending.append({'record_id': i, 'text': items[i]['text'],
                            'monitoring_target': items[i]['monitoring_target'],
                            'A3': A[i], 'C': C[i],
                            'champs_en_desaccord': [f for f in CRIT if crit(A[i], f) != crit(C[i], f)]})
            continue

        text = items[i]['text']
        ann = normalise(src, text, famattrs)
        applied = None
        if i in CORRECTIONS_HUMAINES:
            c = CORRECTIONS_HUMAINES[i]
            if 'sentiment.label' in c:
                ann['sentiment']['label'] = c['sentiment.label']
                ann['sentiment']['evidence'] = []
            if 'aspects' in c:
                ann['aspects'] = c['aspects']
            ann = normalise({**ann, 'monitoring_target': ann['monitoring_target']}, text, famattrs)
            tier, applied = 'correction_humaine', c['motif']

        errs = list(validator.iter_errors(ann))
        if errs:
            invalid.append((i, errs[0].message[:90]))
            continue
        gold.append({'record_id': i, 'text': text,
                     'text_sha256': hashlib.sha256(text.encode('utf-8')).hexdigest(),
                     'context': items[i]['context'], 'confiance': tier,
                     'correction_appliquee': applied,
                     'verdict_humain': hv.get(i), 'annotation': ann})

    (OUT / 'gold_v0.3.jsonl').write_text(
        ''.join(json.dumps(g, ensure_ascii=False) + '\n' for g in gold), encoding='utf-8')
    (OUT / 'arbitrage_requis.jsonl').write_text(
        ''.join(json.dumps(p, ensure_ascii=False) + '\n' for p in pending), encoding='utf-8')

    tiers = Counter(g['confiance'] for g in gold)
    langs = Counter(g['annotation']['language']['dominant'] for g in gold)
    manifest = {
        'version': '0.3.0', 'date': '2026-07-30', 'contrat': SCHEMA.name,
        'total_campagne': len(ids), 'gold': len(gold), 'arbitrage_requis': len(pending),
        'invalides': len(invalid), 'paliers': dict(tiers), 'langues': dict(langs),
        'sentiment': dict(Counter(g['annotation']['sentiment']['label'] for g in gold)),
        'alertes': sum(len(g['annotation']['alerts']) for g in gold),
        'sha256': hashlib.sha256((OUT / 'gold_v0.3.jsonl').read_bytes()).hexdigest(),
        'avertissements': [
            "Les paliers ne sont pas equivalents. accord_A3_C repose sur un accord "
            "machine-machine dont le taux d acceptation humain mesure est de 90 pourcent.",
            "Les 41 items arabizi proviennent de la repasse R1, avec etape de traduction imposee.",
            "harcelement_discrimination n est jamais exercee : ses seuls candidats sont en "
            "scope espace_public ou la regle D1 interdit toute alerte.",
            "Les alertes restent statistiquement non evaluables : ~16 evenements distincts.",
        ]}
    (OUT / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n',
                                       encoding='utf-8')
    print(f'gold V0.3 : {len(gold)} items, {len(pending)} en arbitrage, {len(invalid)} invalides')
    for t, n in tiers.most_common():
        print(f'   {t:20s} {n:4d}')
    if invalid:
        print('  invalides :', invalid[:5])
    print(f'\nlangues   : {dict(langs)}')
    print(f'sentiment : {manifest["sentiment"]}')
    print(f'alertes   : {manifest["alertes"]}')
    print(f'sha256    : {manifest["sha256"][:16]}…')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
