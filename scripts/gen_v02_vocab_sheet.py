#!/usr/bin/env python3
"""Genere la fiche de vocabulaires fermes depuis le schema V0.2.

Resout les $ref et ECHOUE si une enumeration ressort vide : une fiche
incomplete livree a un annotateur est un defaut silencieux.
"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
S = json.loads((ROOT / 'docs/slm_v2/business_comment_annotation_v0.2.schema.json').read_text(encoding='utf-8'))
D = S['$defs']

def deref(n):
    for _ in range(10):
        if isinstance(n, dict) and '$ref' in n:
            n = D[n['$ref'].split('/')[-1]]
        else:
            return n
    return n

def en(node, label):
    node = deref(node)
    vals = node.get('enum')
    if vals is None:
        vals = deref(node.get('items', {})).get('enum')
    if not vals:
        raise SystemExit(f'ENUMERATION VIDE : {label} — $ref non resolu, fiche non ecrite')
    return ' | '.join('null' if v is None else str(v) for v in vals)

L = ['# Vocabulaires fermes — business-comment-annotation v0.2.0\n',
     'Extrait automatiquement du schema. AUCUNE valeur hors de ces listes.\n',
     '## monitoring_target — FOURNI EN ENTREE, ne jamais le modifier\n',
     f"- `scope` : {en(D['monitoringTarget']['properties']['scope'], 'scope')}",
     f"- `entity_type` : {en(D['monitoringTarget']['properties']['entity_type'], 'entity_type')}",
     '\n## Racine\n',
     '- `is_exploitable` : true | false',
     f"- `non_exploitable_reason` : {en(S['properties']['non_exploitable_reason'], 'reason')}",
     f"- `business_relevance` : {en(S['properties']['business_relevance'], 'relevance')}",
     f"- `author_role` : {en(S['properties']['author_role'], 'author_role')}",
     '- `requires_parent_context` : true | false',
     f"- `intents` (0 a 3) : {en(S['properties']['intents']['items'], 'intents')}",
     '\n## language\n']
for k in ('dominant', 'detected', 'scripts'):
    L.append(f"- `{k}` : {en(D['language']['properties'][k], k)}")
L += ['- `code_switching` : true | false',
      '\n## entities (max 10)\n',
      f"- `type` : {en(D['entity']['properties']['type'], 'ent.type')}",
      f"- `source` : {en(D['entity']['properties']['source'], 'ent.source')}",
      '\n## sentiment\n',
      f"- `label` : {en(D['overallSentiment']['properties']['label'], 'sent.label')}",
      f"- `intensity` : {en(D['overallSentiment']['properties']['intensity'], 'sent.intensity')}",
      f"- `emotion` : {en(D['overallSentiment']['properties']['emotion'], 'sent.emotion')}",
      '- `sarcasm` : true | false',
      '\n## aspects (max 8) — couples famille/attribut AUTORISES\n']
for r in D['aspect'].get('allOf', []):
    f = r.get('if', {}).get('properties', {}).get('family', {}).get('const')
    a = r.get('then', {}).get('properties', {}).get('attribute', {}).get('enum')
    if f and a:
        L.append(f'- **{f}** -> {", ".join(a)}')
L += [f"\n- aspect `sentiment` : {en(D['aspect']['properties']['sentiment'], 'asp.sentiment')}"
      '   <- AUCUN aspect neutre en V0.2',
      f"- aspect `intensity` : {en(D['aspect']['properties']['intensity'], 'asp.intensity')}",
      '- aspect `implicit` : true | false',
      '- aspect `attribute` : OPTIONNEL en V0.2. Omets-le si tu hesites.',
      '\n## alerts (max 5)\n',
      f"- `type` : {en(D['alert']['properties']['type'], 'alert.type')}",
      f"- `severity` : {en(D['alert']['properties']['severity'], 'alert.severity')}",
      '\n## actionability — NE PAS PRODUIRE\n',
      "Bloc entierement DERIVE par le pipeline en V0.2. Ne l'inclus pas dans ta sortie.\n"]
out = ROOT / 'data/processed/slm_v2_gold/campaign_v0.2/VOCABULAIRES_FERMES_V0.2.md'
out.write_text('\n'.join(L) + '\n', encoding='utf-8')
txt = out.read_text(encoding='utf-8')
empty = [l for l in txt.splitlines() if l.rstrip().endswith(' :')]
if empty:
    raise SystemExit(f'ECHEC : lignes vides {empty}')
print('ecrit', out, out.stat().st_size, 'octets — 0 enumeration vide')
