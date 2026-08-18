"""
Test standalone du pipeline DziriBERT + hybride RamyPulse.

Lance sans l'app — teste directement les modèles.
Usage:
    python scripts/test_pipeline_dziribert.py
"""

from __future__ import annotations

import io
import os
import sys
import json
from pathlib import Path

# Force UTF-8 output on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ── Setup path ──────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env", override=True)

GEMINI_KEY = os.getenv("GOOGLE_API_KEY", "")
MODEL_DIR = str(ROOT / "models" / "dziribert-sentiment")

# ── Cas de test ─────────────────────────────────────────────────────────────

TEST_CASES = [
    # ── POSITIFS CLAIRS ────────────────────────────────────────────────────
    {
        "id": "POS-01",
        "category": "POSITIF",
        "text": "هاد العصير زوين بزاف، نحبو كثير وندير فيه كل يوم",
        "expected": "positive",
        "note": "Positif clair — Darija pure",
    },
    {
        "id": "POS-02",
        "category": "POSITIF",
        "text": "Ramy c'est le meilleur produit algérien, je le recommande à tout le monde",
        "expected": "positive",
        "note": "Positif clair — français",
    },
    {
        "id": "POS-03",
        "category": "POSITIF",
        "text": "Hamoud Boualem هو الأحسن، تاريخ جزائري أصيل",
        "expected": "positive",
        "note": "Positif clair — mixte arabe/français",
    },

    # ── NÉGATIFS CLAIRS ────────────────────────────────────────────────────
    {
        "id": "NEG-01",
        "category": "NÉGATIF",
        "text": "لقاوها تسقي المزرعة بمياه الصرف الصحي",
        "expected": "negative",
        "note": "Négatif fort — pollution/scandale (issu du dataset réel)",
    },
    {
        "id": "NEG-02",
        "category": "NÉGATIF",
        "text": "عصير Ramy خايب، طعمه مش مليح وغالي بزاف",
        "expected": "negative",
        "note": "Négatif clair — goût + prix",
    },
    {
        "id": "NEG-03",
        "category": "NÉGATIF",
        "text": "هذا المنتج مضر بالصحة، ماشي مليح خالص",
        "expected": "negative",
        "note": "Négatif — santé",
    },

    # ── NEUTRES ────────────────────────────────────────────────────────────
    {
        "id": "NEU-01",
        "category": "NEUTRE",
        "text": "عصير Ramy متاح في كل المحلات بالجزائر بسعر 80 دينار",
        "expected": "neutral",
        "note": "Neutre — information factuelle",
    },
    {
        "id": "NEU-02",
        "category": "NEUTRE",
        "text": "Hamoud Boualem a été fondé en 1878 à Alger",
        "expected": "neutral",
        "note": "Neutre — fait historique",
    },

    # ── CAS HYBRIDES : SARCASME / IRONIE (nécessitent le pipeline complet) ──
    {
        "id": "HYB-01",
        "category": "HYBRIDE (sarcasme)",
        "text": "ممتاز هاد المنتوج ممتاز خلاني مريض 3 يام",
        "expected": "negative",  # DziriBERT dit positif mais pipeline doit flipper
        "note": "Sarcasme algérien classique : ممتاز + مريض — cas test Colab",
    },
    {
        "id": "HYB-02",
        "category": "HYBRIDE (sarcasme)",
        "text": "j'adore comment Ramy met autant de sucre dans son jus, trop bien pour la santé",
        "expected": "negative",
        "note": "Sarcasme français : j'adore + ironique sur la santé",
    },
    {
        "id": "HYB-03",
        "category": "HYBRIDE (ironie)",
        "text": "برافو عليهم، ياسر عندهم الجرأة يبيعوا ماء الصرف الصحي بسعر عصير",
        "expected": "negative",
        "note": "Ironie : برافو sarcastique + إشارة صرف صحي",
    },
    {
        "id": "HYB-04",
        "category": "HYBRIDE (lexicon)",
        "text": "شكراً Ramy على هذا العصير الممتاز الذي يشبه طعم البلاستيك",
        "expected": "negative",
        "note": "Lexicon hit : بلاستيك — goût plastique",
    },
    {
        "id": "HYB-05",
        "category": "HYBRIDE (mixte)",
        "text": "الطعم زوين بصح التغليف خايب والسعر غالي، ماشي مليح هاد العرض",
        "expected": "negative",
        "note": "Mixed : positif sur le goût, négatif sur emballage+prix",
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# Helpers d'affichage
# ─────────────────────────────────────────────────────────────────────────────

LABELS_FR = {
    "positive": "✅ positive",
    "negative": "❌ negative",
    "neutral":  "⚪ neutral",
}

METHODS_FR = {
    "dziribert_direct":      "DziriBERT direct",
    "llm_arbitrage":         "⚡ LLM arbitrage (Gemini)",
    "llm_arbitrage_failed":  "⚠️  LLM arbitrage échoué",
    "incongruity_flagged":   "⚠️  incongruité (sans Gemini)",
    "empty_input":           "— input vide",
}

def _verdict(predicted: str, expected: str) -> str:
    return "✓ CORRECT" if predicted == expected else f"✗ WRONG (attendu: {expected})"


def _bar(prob: float, width: int = 20) -> str:
    filled = int(prob * width)
    return "█" * filled + "░" * (width - filled)


def print_result(case: dict, result) -> None:
    r = result.to_dict()
    label = r["label"]
    conf = r["confidence"]
    method = r["method"]
    dist = r["distribution"]

    print(f"\n{'─'*65}")
    print(f"[{case['id']}] {case['category']}")
    print(f"Texte  : {case['text'][:80]}")
    print(f"Note   : {case['note']}")
    print(f"─" * 40)
    print(f"Résultat : {LABELS_FR.get(label, label)} ({conf:.1%})")
    print(f"Méthode  : {METHODS_FR.get(method, method)}")
    print(f"Verdict  : {_verdict(label, case['expected'])}")

    # Distribution
    print(f"Distribution :")
    for lbl in ["positive", "neutral", "negative"]:
        p = dist.get(lbl, 0)
        print(f"  {lbl:8s} {_bar(p)} {p:.1%}")

    # Incongruité détectée
    if r.get("incongruity"):
        inc = r["incongruity"]
        print(f"Incongruité : {inc.get('reason', '?')} — segment «{inc.get('worst_neg_segment', '')[:40]}» ({inc.get('worst_neg_score', 0):.1%} neg)")

    # Raisonnement LLM
    if r.get("llm_reasoning"):
        print(f"Gemini dit : {r['llm_reasoning'][:120]}")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 65)
    print("   TEST DziriBERT + Pipeline Hybride RamyPulse")
    print("=" * 65)
    print(f"Modèle    : {MODEL_DIR}")
    print(f"Gemini    : {'✓ configuré' if GEMINI_KEY else '✗ ABSENT — mode local pur'}")
    print(f"Cas tests : {len(TEST_CASES)} ({sum(1 for c in TEST_CASES if 'HYBRIDE' in c['category'])} hybrides)")

    # ── Charger le pipeline ──────────────────────────────────────────────
    print("\nChargement DziriBERT...")
    from inference.pipeline import SentimentPipeline
    pipe = SentimentPipeline(
        model_dir=MODEL_DIR,
        gemini_api_key=GEMINI_KEY or None,
    )
    print("Modèle chargé.\n")

    # ── Phase 1 : DziriBERT seul (cas simples) ──────────────────────────
    simple_cases = [c for c in TEST_CASES if "HYBRIDE" not in c["category"]]
    hybrid_cases = [c for c in TEST_CASES if "HYBRIDE" in c["category"]]

    print("\n" + "=" * 65)
    print("  PHASE 1 — DziriBERT standalone (cas simples)")
    print("=" * 65)

    phase1_correct = 0
    for case in simple_cases:
        result = pipe.predict(case["text"])
        print_result(case, result)
        if result.label == case["expected"]:
            phase1_correct += 1

    print(f"\n→ Phase 1 : {phase1_correct}/{len(simple_cases)} corrects")

    # ── Phase 2 : Pipeline hybride (cas ambigus) ─────────────────────────
    print("\n" + "=" * 65)
    print("  PHASE 2 — Pipeline hybride (sarcasme / ironie)")
    print("=" * 65)
    if not GEMINI_KEY:
        print("⚠  Pas de clé Gemini — incongruité détectée mais pas arbitrée")

    phase2_correct = 0
    llm_called = 0
    llm_flipped = 0
    for case in hybrid_cases:
        result = pipe.predict(case["text"])
        print_result(case, result)
        if result.label == case["expected"]:
            phase2_correct += 1
        if result.method == "llm_arbitrage":
            llm_called += 1
        if result.method == "llm_arbitrage" and result.label != "positive":
            llm_flipped += 1

    print(f"\n→ Phase 2 : {phase2_correct}/{len(hybrid_cases)} corrects")
    print(f"  Gemini appelé : {llm_called} fois")
    print(f"  Flips positif→négatif : {llm_flipped}")

    # ── Récap global ─────────────────────────────────────────────────────
    print("\n" + "=" * 65)
    print("  RÉCAPITULATIF")
    print("=" * 65)
    total = len(TEST_CASES)
    total_correct = phase1_correct + phase2_correct
    stats = pipe.get_stats()
    print(f"Total          : {total_correct}/{total} corrects ({total_correct/total:.0%})")
    print(f"Direct (BERT)  : {stats['direct']} textes ({stats.get('direct_pct', 0):.1f}%)")
    print(f"Vérif incongruité : {stats['incongruity_checked']} textes")
    print(f"Arbitrage LLM  : {stats['llm_arbitrated']} textes")
    print(f"Flips total    : {stats['llm_flipped']}")
    print("=" * 65)


if __name__ == "__main__":
    main()
