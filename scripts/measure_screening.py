#!/usr/bin/env python3
"""DziriBERT peut-il servir de premier tri avant le SLM, sans rater d'alerte ?

L'enjeu vient du produit, pas du modele. Le cycle de detection d'alertes est de
30 minutes (`ALERT_DETECTION_INTERVAL_MINUTES`), la collecte Facebook ou
Instagram consomme 5 de ces minutes, la collecte Maps les consomme toutes. Le SLM
traite environ 0,17 commentaire par seconde en flux simple : trois fois moins que
necessaire pour absorber un cycle. DziriBERT en traite 1 737 par seconde.

Si un tri par DziriBERT ecarte ce qui ne peut pas porter d'alerte, le SLM ne voit
plus qu'une fraction du flux, et la fraicheur de l'alerte cesse de dependre de
son debit.

Ce qui se mesure ici est le **rappel**, pas le gain. Un tri qui rate une alerte
grave est inacceptable quelle que soit sa vitesse : c'est la fonction meme du
produit. Le volume economise ne compte que si le rappel reste intact.

Usage :
  python scripts/measure_screening.py [--limit N]
"""
from __future__ import annotations

import argparse
import json
import warnings
from collections import Counter
from pathlib import Path

warnings.filterwarnings('ignore')

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/processed/slm_v2_gold/maps_v0.3'
MODEL = ROOT / 'models/dziribert-sentiment'
LABEL_MAP = {'positive': 'positif', 'negative': 'negatif', 'neutral': 'neutre'}
#: Debit du SLM en flux simple, deduit de 184 tokens a 30 tokens/seconde.
DEBIT_SLM = 0.17
CYCLE_SECONDES = 30 * 60


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int, default=None)
    args = ap.parse_args()

    annotations, textes = {}, {}
    for dossier in ('silver', 'holdout'):
        for f in sorted((BASE / dossier / 'output').glob('*.out.jsonl')):
            for ligne in f.read_text(encoding='utf-8').splitlines():
                if ligne.strip():
                    r = json.loads(ligne)
                    annotations[r['record_id']] = r
        for f in sorted((BASE / dossier / 'input').glob('*.jsonl')):
            for ligne in f.read_text(encoding='utf-8').splitlines():
                if ligne.strip():
                    r = json.loads(ligne)
                    textes[r['record_id']] = r['text']

    ids = [i for i in annotations if i in textes]
    # Les items porteurs d'alerte entrent tous : c'est sur eux que se mesure le
    # rappel, et les echantillonner en diluerait la precision.
    avec_alerte = [i for i in ids if annotations[i]['alerts']]
    if args.limit:
        autres = [i for i in ids if i not in set(avec_alerte)][:args.limit]
        ids = avec_alerte + autres
    print(f'corpus examine : {len(ids)} commentaires, {len(avec_alerte)} avec alerte')

    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(str(MODEL))
    modele = AutoModelForSequenceClassification.from_pretrained(str(MODEL))
    modele.eval()
    id2label = {int(k): v for k, v in json.loads(
        (MODEL / 'config.json').read_text(encoding='utf-8'))['id2label'].items()}

    predictions = {}
    for i in range(0, len(ids), 128):
        lot = ids[i:i + 128]
        batch = tok([textes[x] for x in lot], truncation=True, max_length=128,
                    padding=True, return_tensors='pt')
        with torch.no_grad():
            sortie = modele(**batch).logits
        for rid, indice in zip(lot, sortie.argmax(-1)):
            predictions[rid] = LABEL_MAP[id2label[int(indice)]]
        if i and i % 2560 == 0:
            print(f'  {i}/{len(ids)}', flush=True)

    print(f'\nDziriBERT : {dict(Counter(predictions.values()))}')
    graves = [i for i in avec_alerte
              if any(a['severity'] == 'elevee' for a in annotations[i]['alerts'])]

    print(f"\n{'tri retenu':28s} {'volume garde':>13s} {'rappel alertes':>15s} {'rappel graves':>14s}")
    for nom, garde in (('negatif seul', lambda p: p == 'negatif'),
                       ('negatif ou neutre', lambda p: p in ('negatif', 'neutre')),
                       ('tout sauf positif', lambda p: p != 'positif')):
        gardes = {i for i in ids if garde(predictions[i])}
        rappel = sum(i in gardes for i in avec_alerte) / max(len(avec_alerte), 1)
        rappel_g = sum(i in gardes for i in graves) / max(len(graves), 1)
        print(f'{nom:28s} {len(gardes) / len(ids):12.0%} {rappel:14.1%} {rappel_g:13.1%}')

    manques = [i for i in graves if predictions[i] != 'negatif']
    print(f'\nalertes GRAVES ratees par un tri sur `negatif` : {len(manques)} / {len(graves)}')
    for i in manques[:5]:
        types = [a['type'] for a in annotations[i]['alerts']]
        print(f'  [dziribert={predictions[i]}] {types} | {textes[i][:90]}')

    print(f'\ncapacite d un cycle de 30 min, SLM a {DEBIT_SLM} c/s :')
    for nom, part in (('sans tri', 1.0),
                      ('tri negatif',
                       sum(p == 'negatif' for p in predictions.values()) / len(ids)),
                      ('tri non-positif',
                       sum(p != 'positif' for p in predictions.values()) / len(ids))):
        print(f'  {nom:18s} part {part:4.0%}  ->  '
              f'{CYCLE_SECONDES * DEBIT_SLM / max(part, 1e-9):6.0f} commentaires')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
