"""
Test du pipeline complet (DziriBERT + incongruité + LLM) sur les 9 cas originaux
+ 20 cas adversariaux. Compare DziriBERT seul vs pipeline.

v2 : pipeline avec fenêtre glissante + gemini-2.5-flash (cf. inference/pipeline.py).

Usage Colab :
    !pip install -q transformers google-genai scikit-learn
    # Alternative si google-genai ne marche pas :
    # !pip install -q transformers google-generativeai scikit-learn
    !python evaluation/test_pipeline.py --gemini-key AIzaSyCjk7RJtwbryCdUcbVnFs-BOK9QYnNlgAc
"""

from __future__ import annotations

import sys
import os
import json
from pathlib import Path

# Ajouter le parent pour importer inference/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import torch
import numpy as np
from sklearn.metrics import classification_report, f1_score
from transformers import pipeline as hf_pipeline

from inference.pipeline import SentimentPipeline

# ─────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────

DEFAULT_MODEL_DIR = "/content/drive/MyDrive/RamyPulse/models/dziribert-sentiment"

# Les 9 cas originaux + 20 adversariaux
ALL_CASES = [
    # ── 9 cas originaux (baseline — tous réussis par DziriBERT seul) ──
    {"id": "ORIG-01", "text": "رامي عصير ممتاز والله نحبو بزاف", "expected": "positive", "category": "original"},
    {"id": "ORIG-02", "text": "Ramy jus top qualité", "expected": "positive", "category": "original"},
    {"id": "ORIG-03", "text": "حمود بوعلام ديما الأفضل", "expected": "positive", "category": "original"},
    {"id": "ORIG-04", "text": "المنتوج هذا ماشي مليح خلاص", "expected": "negative", "category": "original"},
    {"id": "ORIG-05", "text": "had el produit dégoûtant wallah", "expected": "negative", "category": "original"},
    {"id": "ORIG-06", "text": "لقاوها تسقي بمياه الصرف الصحي", "expected": "negative", "category": "original"},
    {"id": "ORIG-07", "text": "شحال الثمن تع رامي الجديد؟", "expected": "neutral", "category": "original"},
    {"id": "ORIG-08", "text": "win nlgah ramy f béjaia?", "expected": "neutral", "category": "original"},
    {"id": "ORIG-09", "text": "أنا أشارك شهر مارس", "expected": "neutral", "category": "original"},

    # ── 20 cas adversariaux ──
    {"id": "ADV-01", "text": "Bravo Ramy, 3andkom talent f dégradation ta3 el goût, chaque version plus mauvaise que l'autre", "expected": "negative", "category": "sarcasme"},
    {"id": "ADV-02", "text": "ممتاز هاد المنتوج ممتاز ممتاز خلاني مريض 3 يام", "expected": "negative", "category": "sarcasme"},
    {"id": "ADV-03", "text": "waw Ramy jus top kima l'eau du robinet, bravo l'industrie algérienne", "expected": "negative", "category": "sarcasme"},
    {"id": "ADV-04", "text": "merci Hamoud Boualem, grace à vous j'ai découvert que le plastique a un goût", "expected": "negative", "category": "sarcasme"},
    {"id": "ADV-05", "text": "والله نحب رامي بزاف، كل ما نشربو نتذكر علاش لازم نشرب الماء خير", "expected": "negative", "category": "sarcasme"},
    {"id": "ADV-06", "text": "Ramy jus 😍😍😍 3andou goût ta3 médicament 🤮", "expected": "negative", "category": "emoji_ironique"},
    {"id": "ADV-07", "text": "Hamoud Selecto 👏👏👏 t7awel men produit wa3er l produit bla goût", "expected": "negative", "category": "emoji_ironique"},
    {"id": "ADV-08", "text": "😂😂😂 chrit Ramy w lagitouh périmé, el date maktouba 2028 w el goût ta3 2020", "expected": "negative", "category": "emoji_ironique"},
    {"id": "ADV-09", "text": "🔥🔥🔥 el prix ta3 Ramy, ça fait mal au portefeuille ktar men la soif", "expected": "negative", "category": "emoji_ironique"},
    {"id": "ADV-10", "text": "seriously Ramy ta3kom dégoûtant w overpriced, manzidch neshrih jamais de la vie wallah", "expected": "negative", "category": "code_switch_dense"},
    {"id": "ADV-11", "text": "j'ai try le nouveau parfum ta3 Hamoud, c'est mid wallah, rien de spécial, pas ouf", "expected": "negative", "category": "code_switch_dense"},
    {"id": "ADV-12", "text": "Ramy tropical c trop good, nchorbha every day fi l'été, best jus algérien hands down", "expected": "positive", "category": "code_switch_dense"},
    {"id": "ADV-13", "text": "win nlgah Hamoud Selecto original? partout ghir les copies, même fi Alger center manl9ahch", "expected": "negative", "category": "code_switch_dense"},
    {"id": "ADV-14", "text": "Ramy c'est pas terrible, disons que j'ai connu mieux", "expected": "negative", "category": "negation_subtile"},
    {"id": "ADV-15", "text": "ماشي بزاف مليح هاد العصير بصح ماشي خايب بزاف زعما", "expected": "negative", "category": "negation_subtile"},
    {"id": "ADV-16", "text": "Hamoud Boualem mabkatch kima bekri, le goût ta3 dork est pas le même", "expected": "negative", "category": "negation_subtile"},
    {"id": "ADV-17", "text": "Ramy meilleur que les eaux usées je suppose 😅", "expected": "negative", "category": "faux_positif"},
    {"id": "ADV-18", "text": "نشكر ربي على وجود Ramy باش نعرفو الفرق بين العصير الطبيعي والمصنع", "expected": "negative", "category": "faux_positif"},
    {"id": "ADV-19", "text": "j'adore comment Ramy arrive à mettre autant de sucre et aussi peu de fruit dans un seul jus", "expected": "negative", "category": "faux_positif"},
    {"id": "ADV-20", "text": "ana n7eb Hamoud Boualem, بصح el prix ta3hom 7ram, 200 DA pour une bouteille c du vol", "expected": "negative", "category": "faux_positif"},
]


def run_comparison(model_dir: str, gemini_key: str | None = None):
    """Compare DziriBERT seul vs Pipeline complet."""

    print("=" * 75)
    print("  COMPARAISON : DziriBERT seul vs Pipeline (incongruité + LLM)")
    print("=" * 75)

    # ── 1. DziriBERT seul ──
    print("\n  Chargement DziriBERT seul...")
    device = 0 if torch.cuda.is_available() else -1
    clf = hf_pipeline(
        "text-classification", model=model_dir, tokenizer=model_dir,
        device=device, top_k=None,
    )

    # ── 2. Pipeline complet ──
    print("  Chargement Pipeline complet...")
    pipe = SentimentPipeline(
        model_dir=model_dir,
        gemini_api_key=gemini_key,
    )

    # ── 3. Exécuter ──
    results = []
    for case in ALL_CASES:
        # DziriBERT seul
        raw = clf(case["text"])[0]
        raw_sorted = sorted(raw, key=lambda x: x["score"], reverse=True)
        bert_label = raw_sorted[0]["label"]
        bert_conf = raw_sorted[0]["score"]

        # Pipeline
        pipe_result = pipe.predict(case["text"])

        results.append({
            **case,
            "bert_label": bert_label,
            "bert_conf": round(bert_conf, 4),
            "bert_correct": bert_label == case["expected"],
            "pipe_label": pipe_result.label,
            "pipe_conf": round(pipe_result.confidence, 4),
            "pipe_correct": pipe_result.label == case["expected"],
            "pipe_method": pipe_result.method,
            "incongruity": pipe_result.incongruity,
            "llm_reasoning": pipe_result.llm_reasoning,
        })

    # ── 4. Afficher les résultats ──
    print("\n" + "=" * 75)
    print(f"  {'ID':8s} {'Cat':20s} {'BERT':10s} {'Pipeline':15s} {'Δ'}")
    print("  " + "-" * 70)

    flipped_correct = 0
    flipped_wrong = 0
    for r in results:
        bert_icon = "✅" if r["bert_correct"] else "❌"
        pipe_icon = "✅" if r["pipe_correct"] else "❌"

        delta = ""
        if not r["bert_correct"] and r["pipe_correct"]:
            delta = "🔄 FIXED"
            flipped_correct += 1
        elif r["bert_correct"] and not r["pipe_correct"]:
            delta = "⚠️ BROKEN"
            flipped_wrong += 1
        elif r["pipe_method"] != "dziribert_direct":
            delta = f"({r['pipe_method']})"

        print(f"  {r['id']:8s} {r['category']:20s} {bert_icon}{r['bert_label']:8s}  {pipe_icon}{r['pipe_label']:8s}  {delta}")

        if r.get("llm_reasoning"):
            print(f"           LLM: {r['llm_reasoning'][:80]}")

    # ── 5. Métriques comparatives ──
    print("\n" + "=" * 75)
    print("  MÉTRIQUES COMPARATIVES")
    print("=" * 75)

    # DziriBERT seul
    bert_true = [r["expected"] for r in results]
    bert_pred = [r["bert_label"] for r in results]
    bert_acc = sum(1 for t, p in zip(bert_true, bert_pred) if t == p) / len(bert_true)
    bert_f1 = f1_score(bert_true, bert_pred, average="macro", zero_division=0)

    # Pipeline
    pipe_true = [r["expected"] for r in results]
    pipe_pred = [r["pipe_label"] for r in results]
    pipe_acc = sum(1 for t, p in zip(pipe_true, pipe_pred) if t == p) / len(pipe_true)
    pipe_f1 = f1_score(pipe_true, pipe_pred, average="macro", zero_division=0)

    print(f"\n  {'':25s} {'DziriBERT seul':>15s}  {'Pipeline':>15s}  {'Δ':>10s}")
    print(f"  {'Accuracy':25s} {bert_acc:>14.1%}  {pipe_acc:>14.1%}  {pipe_acc - bert_acc:>+9.1%}")
    print(f"  {'F1 macro':25s} {bert_f1:>14.4f}  {pipe_f1:>14.4f}  {pipe_f1 - bert_f1:>+9.4f}")
    print(f"\n  Cas fixés par le pipeline : {flipped_correct}")
    print(f"  Cas cassés par le pipeline : {flipped_wrong}")

    # Par catégorie
    print(f"\n  {'Catégorie':25s} {'BERT':>8s} {'Pipeline':>8s} {'Δ':>8s}")
    print("  " + "-" * 55)
    categories = sorted(set(r["category"] for r in results))
    for cat in categories:
        cat_results = [r for r in results if r["category"] == cat]
        bert_ok = sum(1 for r in cat_results if r["bert_correct"])
        pipe_ok = sum(1 for r in cat_results if r["pipe_correct"])
        total = len(cat_results)
        diff = pipe_ok - bert_ok
        sign = "+" if diff > 0 else ""
        print(f"  {cat:25s} {bert_ok}/{total:>5d} {pipe_ok}/{total:>5d} {sign}{diff:>6d}")

    # Stats pipeline
    print(f"\n  Stats pipeline : {json.dumps(pipe.get_stats(), indent=2)}")

    # Sauvegarde
    output_path = Path(model_dir).parent / "pipeline_comparison.json"
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n  Résultats sauvegardés : {output_path}")
    except Exception:
        fallback = Path("/content/pipeline_comparison.json")
        with open(fallback, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n  Résultats sauvegardés : {fallback}")


if __name__ == "__main__":
    model_path = DEFAULT_MODEL_DIR
    gemini_key = None

    if "--model" in sys.argv:
        idx = sys.argv.index("--model")
        model_path = sys.argv[idx + 1]

    if "--gemini-key" in sys.argv:
        idx = sys.argv.index("--gemini-key")
        gemini_key = sys.argv[idx + 1]

    run_comparison(model_path, gemini_key)
