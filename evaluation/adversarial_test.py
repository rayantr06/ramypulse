"""
Adversarial stress-test pour DziriBERT Sentiment.

20 cas ciblés : sarcasme algérien, emojis ironiques, code-switching dense,
négation subtile, faux positifs. Conçus pour attaquer le F1 positive (0.692).

Usage Colab :
    1. Monter Drive (le modèle doit être dans Drive/RamyPulse/models/dziribert-sentiment/)
    2. !pip install -q transformers torch scikit-learn
    3. !python adversarial_test.py                         # mode auto
    4. !python adversarial_test.py --model /autre/chemin   # chemin custom
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import torch
import numpy as np
from transformers import pipeline
from sklearn.metrics import classification_report, f1_score

# ──────────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────────

DEFAULT_MODEL_DIR = "/content/drive/MyDrive/RamyPulse/models/dziribert-sentiment"

ADVERSARIAL_CASES = [
    # ── A. SARCASME ALGÉRIEN ──────────────────────────────────────
    # Le modèle n'a vu AUCUN sarcasme dans le training.
    # "bravo" (6x positif), "ممتاز" (positif), "نحب" (positif) = marqueurs forts.
    {
        "id": "ADV-01",
        "text": "Bravo Ramy, 3andkom talent f dégradation ta3 el goût, chaque version plus mauvaise que l'autre",
        "expected": "negative",
        "category": "sarcasme",
        "attack_vector": "bravo+talent = marqueurs 100% positifs dans training",
    },
    {
        "id": "ADV-02",
        "text": "ممتاز هاد المنتوج ممتاز ممتاز خلاني مريض 3 يام",
        "expected": "negative",
        "category": "sarcasme",
        "attack_vector": "ممتاز ×3 puis twist négatif maladie",
    },
    {
        "id": "ADV-03",
        "text": "waw Ramy jus top kima l'eau du robinet, bravo l'industrie algérienne",
        "expected": "negative",
        "category": "sarcasme",
        "attack_vector": "waw+top+bravo triple positif sarcastique",
    },
    {
        "id": "ADV-04",
        "text": "merci Hamoud Boualem, grace à vous j'ai découvert que le plastique a un goût",
        "expected": "negative",
        "category": "sarcasme",
        "attack_vector": "merci+grâce à vous = remerciement sincère en surface",
    },
    {
        "id": "ADV-05",
        "text": "والله نحب رامي بزاف، كل ما نشربو نتذكر علاش لازم نشرب الماء خير",
        "expected": "negative",
        "category": "sarcasme",
        "attack_vector": "نحب بزاف = j'adore (le plus fort positif Derja)",
    },

    # ── B. EMOJIS IRONIQUES ───────────────────────────────────────
    # Dans le training : 😍 = positif, 👏 = positif, 🔥 = positif, 😂 = neutre.
    # Aucun cas où ces emojis accompagnent du négatif.
    {
        "id": "ADV-06",
        "text": "Ramy jus 😍😍😍 3andou goût ta3 médicament 🤮",
        "expected": "negative",
        "category": "emoji_ironique",
        "attack_vector": "😍 positif suivi de contenu négatif + 🤮",
    },
    {
        "id": "ADV-07",
        "text": "Hamoud Selecto 👏👏👏 t7awel men produit wa3er l produit bla goût",
        "expected": "negative",
        "category": "emoji_ironique",
        "attack_vector": "👏 sarcastique — toujours positif dans training",
    },
    {
        "id": "ADV-08",
        "text": "😂😂😂 chrit Ramy w lagitouh périmé, el date maktouba 2028 w el goût ta3 2020",
        "expected": "negative",
        "category": "emoji_ironique",
        "attack_vector": "😂 = neutre dans training, ici rire de dégoût",
    },
    {
        "id": "ADV-09",
        "text": "🔥🔥🔥 el prix ta3 Ramy, ça fait mal au portefeuille ktar men la soif",
        "expected": "negative",
        "category": "emoji_ironique",
        "attack_vector": "🔥 = hype/positif, ici ironie sur le prix",
    },

    # ── C. CODE-SWITCHING DENSE ───────────────────────────────────
    # Le training a du FR+Derja mais pas de triple EN+FR+Arabizi ni de slang Gen-Z.
    {
        "id": "ADV-10",
        "text": "seriously Ramy ta3kom dégoûtant w overpriced, manzidch neshrih jamais de la vie wallah",
        "expected": "negative",
        "category": "code_switch_dense",
        "attack_vector": "EN+FR+Arabizi triple code-switch dans 1 phrase",
    },
    {
        "id": "ADV-11",
        "text": "j'ai try le nouveau parfum ta3 Hamoud, c'est mid wallah, rien de spécial, pas ouf",
        "expected": "negative",
        "category": "code_switch_dense",
        "attack_vector": "FR+EN slang (mid, ouf) + Arabizi = Gen-Z algérien",
    },
    {
        "id": "ADV-12",
        "text": "Ramy tropical c trop good, nchorbha every day fi l'été, best jus algérien hands down",
        "expected": "positive",
        "category": "code_switch_dense",
        "attack_vector": "FR+EN dense positif — test si modèle suit hors-distrib",
    },
    {
        "id": "ADV-13",
        "text": "win nlgah Hamoud Selecto original? partout ghir les copies, même fi Alger center manl9ahch",
        "expected": "negative",
        "category": "code_switch_dense",
        "attack_vector": "Question surface (win → neutre) mais frustration profonde",
    },

    # ── D. NÉGATION SUBTILE / LITOTE ─────────────────────────────
    # BERT se fait piéger par les litotes et doubles négations.
    {
        "id": "ADV-14",
        "text": "Ramy c'est pas terrible, disons que j'ai connu mieux",
        "expected": "negative",
        "category": "negation_subtile",
        "attack_vector": "litote FR — pas terrible = mauvais, mots isolés neutres",
    },
    {
        "id": "ADV-15",
        "text": "ماشي بزاف مليح هاد العصير بصح ماشي خايب بزاف زعما",
        "expected": "negative",
        "category": "negation_subtile",
        "attack_vector": "double négation Derja — ni bon ni mauvais = négatif",
    },
    {
        "id": "ADV-16",
        "text": "Hamoud Boualem mabkatch kima bekri, le goût ta3 dork est pas le même",
        "expected": "negative",
        "category": "negation_subtile",
        "attack_vector": "nostalgie négative sans mots négatifs explicites",
    },

    # ── E. FAUX POSITIFS PIÈGES ──────────────────────────────────
    # Mots très positifs dans un contexte qui retourne le sens.
    {
        "id": "ADV-17",
        "text": "Ramy meilleur que les eaux usées je suppose 😅",
        "expected": "negative",
        "category": "faux_positif",
        "attack_vector": "meilleur = comparatif positif, mais comparaison insultante",
    },
    {
        "id": "ADV-18",
        "text": "نشكر ربي على وجود Ramy باش نعرفو الفرق بين العصير الطبيعي والمصنع",
        "expected": "negative",
        "category": "faux_positif",
        "attack_vector": "نشكر ربي (remerciement fort) → sens: Ramy = artificiel",
    },
    {
        "id": "ADV-19",
        "text": "j'adore comment Ramy arrive à mettre autant de sucre et aussi peu de fruit dans un seul jus",
        "expected": "negative",
        "category": "faux_positif",
        "attack_vector": "j'adore = le plus fort marqueur positif FR, ici sarcastique",
    },
    {
        "id": "ADV-20",
        "text": "ana n7eb Hamoud Boualem, بصح el prix ta3hom 7ram, 200 DA pour une bouteille c du vol",
        "expected": "negative",
        "category": "faux_positif",
        "attack_vector": "début positif (n7eb) puis virage négatif (7ram, vol)",
    },
]

# ──────────────────────────────────────────────────────────────────
# Runner
# ──────────────────────────────────────────────────────────────────

def run_adversarial(model_dir: str = DEFAULT_MODEL_DIR) -> dict:
    """Exécute les 20 cas adversariaux et retourne les métriques."""

    print("=" * 70)
    print("  ADVERSARIAL STRESS-TEST — DziriBERT Sentiment")
    print("=" * 70)
    print(f"  Modèle    : {model_dir}")
    print(f"  Cas       : {len(ADVERSARIAL_CASES)}")
    print(f"  Catégories: sarcasme (5), emoji (4), code-switch (4), négation (3), faux-pos (4)")
    print("=" * 70)

    device = 0 if torch.cuda.is_available() else -1
    clf = pipeline(
        "text-classification",
        model=model_dir,
        tokenizer=model_dir,
        device=device,
        top_k=None,
    )

    y_true, y_pred = [], []
    results_detail = []

    for case in ADVERSARIAL_CASES:
        preds = clf(case["text"])[0]
        preds_sorted = sorted(preds, key=lambda x: x["score"], reverse=True)
        predicted = preds_sorted[0]["label"]
        confidence = preds_sorted[0]["score"]

        y_true.append(case["expected"])
        y_pred.append(predicted)

        match = "✅" if predicted == case["expected"] else "❌"
        dist = " ".join(f"{p['label'][:3]}:{p['score']:.2f}" for p in preds_sorted)

        results_detail.append({
            **case,
            "predicted": predicted,
            "confidence": round(confidence, 4),
            "correct": predicted == case["expected"],
            "distribution": {p["label"]: round(p["score"], 4) for p in preds_sorted},
        })

        print(f"\n  {match} [{case['id']}] {case['category']}")
        print(f"     Texte    : {case['text'][:75]}{'…' if len(case['text']) > 75 else ''}")
        print(f"     Attendu  : {case['expected']:8s} | Prédit : {predicted:8s} ({confidence:.2f})")
        print(f"     Distrib  : {dist}")
        print(f"     Vecteur  : {case['attack_vector']}")

    # ── Métriques globales ──
    print("\n" + "=" * 70)
    print("  RÉSULTATS GLOBAUX")
    print("=" * 70)

    labels = ["positive", "negative", "neutral"]
    present_labels = sorted(set(y_true + y_pred))

    accuracy = sum(1 for t, p in zip(y_true, y_pred) if t == p) / len(y_true)
    f1_macro = f1_score(y_true, y_pred, labels=present_labels, average="macro", zero_division=0)

    print(f"\n  Accuracy globale  : {accuracy:.1%} ({sum(1 for t, p in zip(y_true, y_pred) if t == p)}/{len(y_true)})")
    print(f"  F1 macro          : {f1_macro:.4f}")
    print(f"\n{classification_report(y_true, y_pred, labels=present_labels, digits=4, zero_division=0)}")

    # ── Métriques par catégorie ──
    print("  PAR CATÉGORIE D'ATTAQUE :")
    print("  " + "-" * 50)
    categories = {}
    for case, pred in zip(ADVERSARIAL_CASES, y_pred):
        cat = case["category"]
        if cat not in categories:
            categories[cat] = {"correct": 0, "total": 0, "failures": []}
        categories[cat]["total"] += 1
        if pred == case["expected"]:
            categories[cat]["correct"] += 1
        else:
            categories[cat]["failures"].append(case["id"])

    for cat, stats in categories.items():
        pct = stats["correct"] / stats["total"]
        bar = "█" * int(pct * 10) + "░" * (10 - int(pct * 10))
        fails = ", ".join(stats["failures"]) if stats["failures"] else "—"
        print(f"  {cat:25s} {bar} {stats['correct']}/{stats['total']} ({pct:.0%})  échoués: {fails}")

    # ── Diagnostic ──
    print("\n  DIAGNOSTIC :")
    print("  " + "-" * 50)

    false_positives = [r for r in results_detail if r["expected"] == "negative" and r["predicted"] == "positive"]
    false_neutrals = [r for r in results_detail if r["expected"] == "negative" and r["predicted"] == "neutral"]

    if false_positives:
        print(f"\n  ⚠️  {len(false_positives)} négatifs classés POSITIFS (sarcasme non détecté) :")
        for fp in false_positives:
            print(f"     → {fp['id']} ({fp['category']}): conf={fp['confidence']:.2f}")

    if false_neutrals:
        print(f"\n  ⚠️  {len(false_neutrals)} négatifs classés NEUTRES (négation subtile ratée) :")
        for fn in false_neutrals:
            print(f"     → {fn['id']} ({fn['category']}): conf={fn['confidence']:.2f}")

    correct_sarcasm = sum(1 for r in results_detail if r["category"] == "sarcasme" and r["correct"])
    if correct_sarcasm <= 1:
        print("\n  🔴 SARCASME : Le modèle ne détecte quasiment pas le sarcasme.")
        print("     → Normal : 0 exemple sarcastique dans le training set.")
        print("     → Fix : ajouter ~50 exemples sarcastiques annotés pour v3.")
    elif correct_sarcasm <= 3:
        print(f"\n  🟡 SARCASME : {correct_sarcasm}/5 détectés — partiel.")
    else:
        print(f"\n  🟢 SARCASME : {correct_sarcasm}/5 détectés — robuste.")

    # ── Sauvegarde JSON ──
    output = {
        "model_dir": model_dir,
        "total_cases": len(ADVERSARIAL_CASES),
        "accuracy": round(accuracy, 4),
        "f1_macro": round(f1_macro, 4),
        "categories": categories,
        "details": results_detail,
    }

    output_path = Path(model_dir).parent / "adversarial_results.json"
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"\n  Résultats sauvegardés : {output_path}")
    except Exception:
        # Fallback si pas d'accès écriture au dossier Drive
        fallback = Path("/content/adversarial_results.json")
        with open(fallback, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"\n  Résultats sauvegardés : {fallback}")

    return output


if __name__ == "__main__":
    model_path = DEFAULT_MODEL_DIR
    if "--model" in sys.argv:
        idx = sys.argv.index("--model")
        if idx + 1 < len(sys.argv):
            model_path = sys.argv[idx + 1]

    run_adversarial(model_path)
