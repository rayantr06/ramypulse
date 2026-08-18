#!/usr/bin/env python3
"""Contrôle d'arabizi par DziriBERT sur des annotations produites par un LLM.

Pourquoi. Deux annotateurs LLM indépendants se replient sur `neutre` en arabizi
— 56 % contre 41 % ailleurs — et leur accord y est le PLUS élevé du corpus alors
que leur validité y est la plus basse. L'accord inter-annotateurs ne peut donc
pas détecter ce défaut : les deux se trompent ensemble.

DziriBERT (`alger-ia/dziribert`, préentraîné sur 1,1 M de tweets algériens) ne
partage pas ce biais. Mesuré sur les 41 items arabizi du corpus V0.2 :

    taux de `neutre`        DziriBERT 12 %  ·  passe validée 12 %  ·  passe biaisée 56 %
    vérité terrain humaine  3 / 3 correctes, là où les deux LLM avaient échoué

Il ne remplace pas l'annotation — 3 classes seulement, F1 macro 0,78. Mais il
constitue un second avis natif algérien, gratuit et local, qui signale les
désaccords à relire. C'est le même rôle que la note en étoiles de Google Maps
ou les étiquettes de Mendeley, sauf que celui-ci parle algérien.

Usage :
  python scripts/dziribert_arabizi_check.py --input <dossier ou fichier .out.jsonl>
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import warnings
from collections import Counter
from pathlib import Path

warnings.filterwarnings('ignore')

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / 'models/dziribert-sentiment'
ARABIZI = re.compile(r'\b(?=[A-Za-z0-9]*[A-Za-z])(?=[A-Za-z0-9]*[2379])[A-Za-z0-9]{3,}\b')
ARABIC = re.compile(r'[؀-ۿ]')
#: DziriBERT ne connaît que 3 classes ; `mixte` n'est pas comparable.
LABEL_MAP = {'positive': 'positif', 'negative': 'negatif', 'neutral': 'neutre'}


def is_arabizi(text: str) -> bool:
    return bool(ARABIZI.search(text)) and not ARABIC.search(text)


def load_annotations(path: Path) -> dict:
    rows = {}
    files = sorted(path.glob('*.out.jsonl')) if path.is_dir() else [path]
    for f in files:
        for line in f.read_text(encoding='utf-8').splitlines():
            if line.strip():
                r = json.loads(line)
                rows[r['record_id']] = r
    return rows


def load_texts(paths: list[Path]) -> dict:
    texts = {}
    for p in paths:
        files = sorted(p.glob('*.jsonl')) if p.is_dir() else [p]
        for f in files:
            for line in f.read_text(encoding='utf-8').splitlines():
                if line.strip():
                    r = json.loads(line)
                    if 'text' in r:
                        texts[r['record_id']] = r['text']
    return texts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', required=True, help='dossier ou fichier .out.jsonl annoté')
    ap.add_argument('--texts', action='append', required=True,
                    help='dossier ou fichier contenant les textes source (répétable)')
    ap.add_argument('--out', default=None, help='fichier des désaccords à relire')
    args = ap.parse_args()

    if not MODEL.exists():
        print(f'modèle absent : {MODEL}', file=sys.stderr)
        return 1

    import torch
    from transformers import AutoTokenizer, AutoModelForSequenceClassification

    annotations = load_annotations(Path(args.input))
    texts = load_texts([Path(p) for p in args.texts])
    pairs = [(rid, texts[rid]) for rid in annotations
             if rid in texts and is_arabizi(texts[rid])]
    if not pairs:
        print('aucun item arabizi dans ce lot')
        return 0

    tok = AutoTokenizer.from_pretrained(str(MODEL))
    model = AutoModelForSequenceClassification.from_pretrained(str(MODEL))
    model.eval()
    id2label = {int(k): v for k, v in
                json.loads((MODEL / 'config.json').read_text(encoding='utf-8'))['id2label'].items()}

    predictions = []
    for i in range(0, len(pairs), 32):
        batch = tok([t for _, t in pairs[i:i + 32]], truncation=True,
                    max_length=128, padding=True, return_tensors='pt')
        with torch.no_grad():
            logits = model(**batch).logits
        predictions += [LABEL_MAP[id2label[int(x)]] for x in logits.argmax(-1)]

    disagreements = []
    for (rid, text), pred in zip(pairs, predictions):
        annotated = annotations[rid]['sentiment']['label']
        # `mixte` est hors du champ de DziriBERT : pas de désaccord exploitable.
        if annotated == 'mixte' or annotated == pred:
            continue
        disagreements.append({'record_id': rid, 'text': text,
                              'annote': annotated, 'dziribert': pred,
                              'lecture_fr': annotations[rid].get('lecture_fr', '')})

    neutral_rate = sum(p == 'neutre' for p in predictions) / len(predictions)
    annotated_neutral = sum(annotations[r]['sentiment']['label'] == 'neutre'
                            for r, _ in pairs) / len(pairs)

    print(f'items arabizi         : {len(pairs)}')
    print(f'taux neutre annotateur: {annotated_neutral:.0%}')
    print(f'taux neutre DziriBERT : {neutral_rate:.0%}')
    print(f'désaccords à relire   : {len(disagreements)} ({len(disagreements) / len(pairs):.0%})')
    print(f'  détail : {dict(Counter((d["annote"], d["dziribert"]) for d in disagreements))}')

    if annotated_neutral - neutral_rate > 0.20:
        print('\nALERTE — l annotateur produit beaucoup plus de neutres que DziriBERT.')
        print('         C est la signature du repli observé sur les passes biaisées.')
    else:
        print('\nPas de repli sur neutre détectable sur ce lot.')

    if args.out and disagreements:
        p = Path(args.out)
        p.write_text(''.join(json.dumps(d, ensure_ascii=False) + '\n' for d in disagreements),
                     encoding='utf-8')
        print(f'\ndésaccords écrits : {p}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
