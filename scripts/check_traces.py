#!/usr/bin/env python3
"""Controles mecaniques des traces, sur la totalite du lot.

L'audit confie six verifications au critique independant. Quatre d'entre elles
sont deterministes et n'ont rien a faire dans un prompt : un script les fait
exactement, sur 100 % du corpus, pour rien.

  1. chaque preuve existe exactement aux offsets annonces
  2. aucun label de la trace n'est absent du JSON
  3. aucun label important du JSON n'est oublie dans la trace
  6. la longueur respecte le plafond

Ne restent au critique que les deux qui demandent un jugement : l'ajout de
connaissance externe, et le rattachement de la negation, du sarcasme et des
cibles. Faire relire le reste par un modele coute cher et rend un resultat moins
sur qu'une comparaison de chaines.

Usage :
  python scripts/check_traces.py --traces <dir> --annotations <dir> --texts <dir>
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

#: Labels qui doivent apparaitre dans la trace compacte s'ils sont dans le JSON.
#: L'attribut d'aspect en est exclu : aucune porte ne l'evalue.
ETIQUETTES = ('sentiment', 'aspects', 'alerts')


def charger(dossier: Path, motif: str) -> dict:
    rows = {}
    for f in sorted(dossier.glob(motif)):
        for ligne in f.read_text(encoding='utf-8').splitlines():
            if ligne.strip():
                r = json.loads(ligne)
                rows[r['record_id']] = r
    return rows


def controler(trace: dict, annotation: dict, texte: str) -> list[str]:
    """Retourne la liste des defauts. Vide si la trace est saine."""
    defauts = []
    t = trace['decision_trace']
    compacte = trace['compact_trace']

    # 1. Les preuves doivent exister telles quelles, aux positions annoncees.
    for e in t['evidence_map']:
        if texte[e['start']:e['end']] != e['text']:
            defauts.append('preuve_offset_faux')
            break
        if e['text'] not in texte:
            defauts.append('preuve_absente')
            break

    # 2. Rien dans la trace qui ne soit dans le JSON. On compare les etiquettes
    #    fermees, pas la prose : c'est ce qui rend le controle exact.
    dec = t['decisions']
    if dec['overall_sentiment']['label'] != (annotation.get('sentiment') or {}).get('label'):
        defauts.append('sentiment_divergent')
    trace_aspects = {(a['family'], a['sentiment']) for a in dec['aspects']}
    json_aspects = {(a['family'], a['sentiment']) for a in annotation.get('aspects') or []}
    if trace_aspects != json_aspects:
        defauts.append('aspects_divergents')
    trace_alertes = {(a['type'], a['severity']) for a in dec['alerts']}
    json_alertes = {(a['type'], a['severity']) for a in annotation.get('alerts') or []}
    if trace_alertes != json_alertes:
        defauts.append('alertes_divergentes')

    # 3. Ce que le JSON porte d'important doit se lire dans la trace compacte.
    for famille, sentiment in json_aspects:
        if famille not in compacte:
            defauts.append('aspect_absent_de_la_trace')
            break
    for type_alerte, _ in json_alertes:
        if type_alerte not in compacte:
            defauts.append('alerte_absente_de_la_trace')
            break

    # 6. Plafond de tokens, mesure a la projection.
    c = t['complexity']
    if c['observed_trace_tokens'] > c['max_trace_tokens']:
        defauts.append('plafond_depasse')

    # Une alerte sans preuve n'est pas verifiable : l'audit la rejette.
    if any(not a.get('evidence_ids') for a in dec['alerts']):
        defauts.append('alerte_sans_preuve')

    # Aucun identifiant de preuve cite dans la trace ne doit etre inconnu.
    connus = {e['id'] for e in t['evidence_map']}
    cites = set(re.findall(r'\bev_\d+\b', compacte))
    if cites - connus:
        defauts.append('preuve_inconnue_citee')
    return defauts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--traces', required=True)
    ap.add_argument('--annotations', required=True)
    ap.add_argument('--texts', action='append', required=True)
    ap.add_argument('--out', default=None, help='fichier des traces en defaut')
    args = ap.parse_args()

    traces = charger(Path(args.traces), '*.trace.jsonl')
    annotations = charger(Path(args.annotations), '*.out.jsonl')
    textes = {}
    for d in args.texts:
        p = Path(d)
        for f in (sorted(p.glob('*.jsonl')) if p.is_dir() else [p]):
            for ligne in f.read_text(encoding='utf-8').splitlines():
                if ligne.strip():
                    r = json.loads(ligne)
                    if 'text' in r:
                        textes[r['record_id']] = r['text']

    motifs: Counter[str] = Counter()
    fautives = []
    examinees = 0
    for rid, trace in traces.items():
        if rid not in annotations or rid not in textes:
            continue
        examinees += 1
        defauts = controler(trace, annotations[rid], textes[rid])
        if defauts:
            for d in defauts:
                motifs[d] += 1
            fautives.append({'record_id': rid, 'defauts': defauts})

    print(f'traces examinees : {examinees}')
    print(f'saines           : {examinees - len(fautives)} = '
          f'{(examinees - len(fautives)) / max(examinees, 1):.1%}')
    print(f'en defaut        : {len(fautives)}')
    for motif, n in motifs.most_common():
        print(f'  {n:5d}  {motif}')
    # Le taux de signalement du professeur, a titre de comparaison.
    doutes = sum(1 for t in traces.values() if not t.get('justifiable', True))
    print(f'\nsignalees par le professeur lui-meme : {doutes} = {doutes / max(examinees, 1):.1%}')
    if args.out and fautives:
        Path(args.out).write_text(
            ''.join(json.dumps(x, ensure_ascii=False) + '\n' for x in fautives),
            encoding='utf-8')
        print(f'ecrit : {args.out}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
