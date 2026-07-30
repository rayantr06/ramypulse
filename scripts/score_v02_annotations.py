#!/usr/bin/env python3
"""Valide et dépouille les annotations de la campagne V0.2.

Fait trois choses :
  1. reconstitue les offsets depuis les preuves littérales et dérive
     `actionability` (D2/D3), puis valide contre le schéma V0.2 ;
  2. calcule l'accord inter-annotateurs quand deux passes sont présentes ;
  3. compare le résultat aux valeurs simulées lors de la décision V0.2.

Usage :
  python scripts/score_v02_annotations.py --annotator output
  python scripts/score_v02_annotations.py --annotator output --annotator output_c
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN = ROOT / 'data/processed/slm_v2_gold/campaign_v0.2'
SCHEMA_PATH = ROOT / 'docs/slm_v2/business_comment_annotation_v0.2.schema.json'

QUEUE_BY_FAMILY = {
    'produit_service': 'produit', 'prix_valeur': 'pricing',
    'disponibilite_acces': 'logistique', 'experience_client': 'service_client',
    'service_client_sav': 'service_client', 'livraison_logistique': 'logistique',
    'digital_technologie': 'digital', 'communication_information': 'communication',
    'confiance_reputation': 'communication', 'operations_processus': 'operations',
    'emploi_management': 'rh', 'securite_conformite': 'securite_qualite',
    'ethique_impact': 'direction', 'marche_innovation': 'direction',
    'infrastructure_service_public': 'service_public',
}
SEV = {'faible': 1, 'moyenne': 2, 'elevee': 3, 'critique': 4}
SEV_INV = {v: k for k, v in SEV.items()}
NEG_ORDER = {'negatif': 0, 'mixte': 1, 'positif': 2}
INT_ORDER = {'forte': 0, 'moyenne': 1, 'faible': 2}


def dominant_aspect(aspects: list[dict]) -> dict | None:
    if not aspects:
        return None
    return sorted(aspects, key=lambda a: (NEG_ORDER.get(a.get('sentiment'), 9),
                                          INT_ORDER.get(a.get('intensity'), 9)))[0]


def derive_actionability(row: dict) -> dict:
    """D2 et D3 : queue et priority sont calculées, jamais annotées."""
    alerts = row.get('alerts') or []
    aspects = row.get('aspects') or []
    org = (row.get('monitoring_target') or {}).get('scope') == 'organisation'
    if alerts and org:
        priority = SEV_INV[max(SEV[a['severity']] for a in alerts)]
    elif org and any(a.get('sentiment') == 'negatif' and a.get('intensity') == 'forte'
                     for a in aspects):
        priority = 'moyenne'
    else:
        priority = 'faible'
    dom = dominant_aspect(aspects)
    queue = QUEUE_BY_FAMILY.get(dom['family'], 'aucune') if (dom and org) else 'aucune'
    actionable = bool(org and (alerts or (dom and dom.get('sentiment') in ('negatif', 'mixte'))))
    if not actionable:
        queue, priority = 'aucune', 'faible'
    return {'actionable': actionable, 'queue': queue, 'priority': priority}


def resolve_offsets(evidence: list, text: str, errors: list, rid: str, where: str) -> list:
    """Les preuves arrivent en texte brut ; le pipeline calcule les positions."""
    out, cursor = [], 0
    for ev in evidence:
        if not isinstance(ev, str) or not ev:
            errors.append((rid, where, 'preuve vide ou non textuelle'))
            continue
        start = text.find(ev, cursor)
        if start < 0:
            start = text.find(ev)
        if start < 0:
            errors.append((rid, where, f'preuve absente du texte : {ev[:40]!r}'))
            continue
        cursor = start + len(ev)
        out.append({'text': ev, 'start': start, 'end': start + len(ev)})
    return out


def normalise(row: dict, text: str, errors: list) -> dict:
    """Le schéma interdit les propriétés additionnelles : record_id, annotator et
    notes sont des métadonnées de campagne et doivent être retirés avant validation."""
    rid = row.get('record_id', '?')
    out = {k: v for k, v in row.items() if k not in ('annotator', 'notes', 'record_id')}
    out['schema_version'] = '0.2.0'
    sent = dict(out.get('sentiment') or {})
    sent['evidence'] = resolve_offsets(sent.get('evidence') or [], text, errors, rid, 'sentiment')
    out['sentiment'] = sent
    for key in ('aspects', 'alerts'):
        items = []
        for it in out.get(key) or []:
            it = dict(it)
            it['evidence'] = resolve_offsets(it.get('evidence') or [], text, errors, rid, key)
            items.append(it)
        out[key] = items
    for ent in out.get('entities') or []:
        if ent.get('source') == 'texte' and isinstance(ent.get('mention'), str):
            s = text.find(ent['mention'])
            if s < 0:
                errors.append((rid, 'entity', f"mention absente : {ent['mention'][:40]!r}"))
            else:
                ent['start'], ent['end'] = s, s + len(ent['mention'])
        else:
            ent['mention'], ent['start'], ent['end'] = None, None, None
    out['actionability'] = derive_actionability(out)
    return out


def load_inputs() -> dict:
    items = {}
    for p in sorted((CAMPAIGN / 'input').glob('batch_*.jsonl')):
        for line in p.read_text(encoding='utf-8').splitlines():
            if line.strip():
                r = json.loads(line)
                items[r['record_id']] = r
    return items


def load_annotator(folder: str) -> dict:
    rows, d = {}, CAMPAIGN / folder
    if not d.exists():
        return rows
    for p in sorted(d.glob('batch_*.out.jsonl')):
        for n, line in enumerate(p.read_text(encoding='utf-8').splitlines(), 1):
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError as exc:
                print(f'  JSON invalide {p.name}:{n} — {exc}', file=sys.stderr)
                continue
            rows[r['record_id']] = r
    return rows


def kappa(pairs):
    n = len(pairs)
    if not n:
        return 0.0, 0.0
    po = sum(a == b for a, b in pairs) / n
    ca, cb = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    pe = sum(ca[k] / n * cb[k] / n for k in set(ca) | set(cb))
    return po, (po - pe) / (1 - pe) if pe < 1 else 1.0


def micro_f1(pairs):
    tp = fp = fn = 0
    for sa, sb in pairs:
        sa, sb = set(sa), set(sb)
        tp += len(sa & sb); fn += len(sa - sb); fp += len(sb - sa)
    p = tp / (tp + fp) if tp + fp else 1.0
    r = tp / (tp + fn) if tp + fn else 1.0
    return (2 * p * r / (p + r) if p + r else 1.0), p, r


SIMULATED = {'business_relevance': 0.942, 'actionable': 0.917, 'priority': 1.000,
             'queue': 0.675, 'aspects': 0.640, 'alerts': 0.667, 'sentiment': 0.788}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--annotator', action='append', required=True,
                    help='dossier sous campaign_v0.2 (repetable)')
    args = ap.parse_args()

    schema = json.loads(SCHEMA_PATH.read_text(encoding='utf-8'))
    validator = Draft202012Validator(schema)
    inputs = load_inputs()
    print(f'entrees : {len(inputs)}')

    passes = {}
    for folder in args.annotator:
        raw = load_annotator(folder)
        if not raw:
            print(f'  [{folder}] aucune sortie trouvee'); continue
        errors, schema_err, ok = [], [], {}
        for rid, row in raw.items():
            if rid not in inputs:
                errors.append((rid, 'input', 'record_id inconnu')); continue
            norm = normalise(row, inputs[rid]['text'], errors)
            errs = list(validator.iter_errors(norm))
            if errs:
                schema_err.append((rid, errs[0].message[:110]))
            else:
                ok[rid] = norm
        missing = sorted(set(inputs) - set(raw))
        print(f'\n[{folder}] recues={len(raw)}  valides={len(ok)}  '
              f'erreurs_schema={len(schema_err)}  preuves_ko={len(errors)}  manquantes={len(missing)}')
        for x in errors[:5]:
            print('   preuve :', x)
        for x in schema_err[:5]:
            print('   schema :', x)
        out = CAMPAIGN / folder / 'normalized.jsonl'
        out.write_text(''.join(json.dumps(v, ensure_ascii=False) + '\n' for v in ok.values()),
                       encoding='utf-8')
        print(f'   normalise -> {out.relative_to(ROOT)}')
        passes[folder] = ok

    names = [f for f in args.annotator if f in passes]
    if len(names) < 2:
        print('\nUne seule passe : accord non calculable.')
        return 0

    a, b = passes[names[0]], passes[names[1]]
    ids = sorted(set(a) & set(b))
    if not ids:
        print('\nAucune paire valide commune : accord non calculable. '
              'Corrigez d abord les erreurs de schema ci-dessus.')
        return 1
    print(f'\n=== ACCORD {names[0]} vs {names[1]} — {len(ids)} paires ===')
    print(f"{'champ':30s} {'mesure':>8s} {'simule':>8s} {'ecart':>8s}")
    cats = [('is_exploitable', lambda x: x['is_exploitable'], None),
            ('business_relevance', lambda x: x['business_relevance'], 'business_relevance'),
            ('language.dominant', lambda x: x['language']['dominant'], None),
            ('author_role', lambda x: x['author_role'], None),
            ('requires_parent_context', lambda x: x['requires_parent_context'], None),
            ('sentiment.label', lambda x: x['sentiment']['label'], 'sentiment'),
            ('actionable', lambda x: x['actionability']['actionable'], 'actionable'),
            ('queue', lambda x: x['actionability']['queue'], 'queue'),
            ('priority', lambda x: x['actionability']['priority'], 'priority')]
    for name, f, key in cats:
        _, k = kappa([(f(a[i]), f(b[i])) for i in ids])
        sim = SIMULATED.get(key)
        gap = f'{k - sim:+.3f}' if sim else '-'
        print(f'{name:30s} {k:8.3f} {sim if sim else "-":>8} {gap:>8}')
    multis = [('intents', lambda x: x['intents'], None),
              ('aspects famille+sentiment',
               lambda x: [(y['family'], y['sentiment']) for y in x['aspects']], 'aspects'),
              ('alerts type+severite',
               lambda x: [(y['type'], y['severity']) for y in x['alerts']], 'alerts')]
    for name, f, key in multis:
        f1, p, r = micro_f1([(f(a[i]), f(b[i])) for i in ids])
        sim = SIMULATED.get(key)
        gap = f'{f1 - sim:+.3f}' if sim else '-'
        print(f'{name:30s} {f1:8.3f} {sim if sim else "-":>8} {gap:>8}   P={p:.2f} R={r:.2f}')
    n_alerts = sum(len(a[i]['alerts']) for i in ids)
    print(f'\nalertes positives cote {names[0]} : {n_alerts} '
          f'(cible >= 30 pour rendre la porte alerte evaluable)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
