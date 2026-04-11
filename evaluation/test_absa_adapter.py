"""Test de l'ABSA adapter avec propagation global → aspect.

Vérifie que le sarcasme détecté au niveau global se propage correctement
aux aspects individuels, même quand la phrase isolée de l'aspect semble positive.

Usage Colab :
    !pip install -q transformers google-genai scikit-learn
    !python evaluation/test_absa_adapter.py --gemini-key AIzaSyCjk7RJtwbryCdUcbVnFs-BOK9QYnNlgAc
"""

from __future__ import annotations

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# ─────────────────────────────────────────────────────────────────────
# Cas de test ABSA — commentaires avec aspects + sarcasme/ironie
# ─────────────────────────────────────────────────────────────────────

ABSA_TEST_CASES = [
    # ── Cas normaux (pas de conflit) ──
    {
        "id": "ABSA-01",
        "text": "الطعم ممتاز بصح السعر غالي بزاف",
        "expected_global": "negative",  # global négatif (prix cher domine)
        "expected_aspects": {
            "goût": "positive_or_negative",  # selon le modèle
            "prix": "negative",
        },
        "category": "normal_multi_aspect",
    },
    {
        "id": "ABSA-02",
        "text": "Ramy tropical c trop good, nchorbha every day fi l'été",
        "expected_global": "positive",
        "expected_aspects": {},  # pas de mot-clé aspect détectable
        "category": "normal_positive",
    },

    # ── Cas sarcasme avec aspect (le problème à résoudre) ──
    {
        "id": "ABSA-03",
        "text": "Bravo Ramy, 3andkom talent f dégradation ta3 el goût, chaque version plus mauvaise que l'autre",
        "expected_global": "negative",
        "expected_aspects": {
            "goût": "negative",  # doit être négatif malgré "talent"
        },
        "category": "sarcasme_single_phrase",
    },
    {
        "id": "ABSA-04",
        "text": "merci Hamoud Boualem, grace à vous j'ai découvert que le plastique a un goût",
        "expected_global": "negative",
        "expected_aspects": {
            "goût": "negative",
            "emballage": "negative",
        },
        "category": "sarcasme_single_phrase",
    },
    {
        "id": "ABSA-05",
        "text": "Ramy jus 😍😍😍 3andou goût ta3 médicament 🤮",
        "expected_global": "negative",
        "expected_aspects": {
            "goût": "negative",
        },
        "category": "emoji_ironique",
    },
    {
        "id": "ABSA-06",
        "text": "😂😂😂 chrit Ramy w lagitouh périmé, el date maktouba 2028 w el goût ta3 2020",
        "expected_global": "negative",
        "expected_aspects": {
            "goût": "negative",
            "fraîcheur": "negative",
        },
        "category": "emoji_ironique",
    },

    # ── Cas cross-phrase (aspect dans une phrase, twist dans l'autre) ──
    {
        "id": "ABSA-07",
        "text": "Le goût est excellent wallah. Mais bon après 2h j'étais malade donc bon.",
        "expected_global": "negative",
        "expected_aspects": {
            "goût": "negative",  # propagation attendue : global négatif → aspect positif = conflit
        },
        "category": "cross_phrase_sarcasm",
    },
    {
        "id": "ABSA-08",
        "text": "El prix raisonnable, ça va. Bla goût kima l'eau, bla qualité, bla fraîcheur.",
        "expected_global": "negative",
        "expected_aspects": {
            "prix": "positive_or_neutral",  # prix OK — pas de propagation (global neg + aspect pos sur prix != sarcasme, c'est un aspect indépendant)
            "goût": "negative",
            "fraîcheur": "negative",
        },
        "category": "mixed_legitimate",
    },

    # ── Cas faux-positif sarcasme avec aspect ──
    {
        "id": "ABSA-09",
        "text": "🔥🔥🔥 el prix ta3 Ramy, ça fait mal au portefeuille ktar men la soif",
        "expected_global": "negative",
        "expected_aspects": {
            "prix": "negative",
        },
        "category": "faux_positif_aspect",
    },
    {
        "id": "ABSA-10",
        "text": "j'adore comment Ramy arrive à mettre autant de sucre et aussi peu de fruit dans un seul jus",
        "expected_global": "negative",
        "expected_aspects": {},  # pas de mot-clé aspect standard
        "category": "sarcasme_no_aspect",
    },
]


def run_absa_tests(model_dir: str, gemini_key: str | None = None):
    """Exécute les tests ABSA adapter."""
    import os
    if gemini_key:
        os.environ["GEMINI_API_KEY"] = gemini_key

    # Force le chargement de l'adapter sentiment
    from core.analysis.sentiment_adapter import SentimentAdapter
    _adapter = SentimentAdapter(model_dir=model_dir, gemini_api_key=gemini_key)

    # Monkey-patch classify_sentiment pour utiliser notre adapter
    import core.analysis.absa_adapter as absa_mod
    absa_mod.classify_sentiment = _adapter.predict

    from core.analysis.absa_adapter import analyze_text

    print("=" * 80)
    print("  TEST ABSA ADAPTER — Propagation Global → Aspect")
    print("=" * 80)

    results = []
    for case in ABSA_TEST_CASES:
        analysis = analyze_text(case["text"])

        # Vérifier sentiment global
        global_label_3 = analysis.get("global_sentiment", "")
        # Mapper 5→3 pour comparaison
        if global_label_3 in ("très_positif", "positif"):
            global_3 = "positive"
        elif global_label_3 in ("très_négatif", "négatif"):
            global_3 = "negative"
        else:
            global_3 = "neutral"

        global_ok = global_3 == case["expected_global"]

        # Vérifier aspects
        aspect_results = {}
        for asp_sent in analysis.get("aspect_sentiments", []):
            asp_name = asp_sent["aspect"]
            asp_label = asp_sent["sentiment"]
            propagated = asp_sent.get("propagated", False)

            # Mapper 5→3
            if asp_label in ("très_positif", "positif"):
                asp_3 = "positive"
            elif asp_label in ("très_négatif", "négatif"):
                asp_3 = "negative"
            else:
                asp_3 = "neutral"

            expected = case["expected_aspects"].get(asp_name)
            if expected == "positive_or_negative":
                asp_ok = True  # flexible
            elif expected == "positive_or_neutral":
                asp_ok = asp_3 in ("positive", "neutral")
            elif expected:
                asp_ok = asp_3 == expected
            else:
                asp_ok = True  # pas d'attendu spécifique

            aspect_results[asp_name] = {
                "label": asp_label,
                "label_3": asp_3,
                "expected": expected,
                "ok": asp_ok,
                "propagated": propagated,
                "reason": asp_sent.get("reason", ""),
            }

        all_aspects_ok = all(r["ok"] for r in aspect_results.values())

        results.append({
            **case,
            "global_pred": global_label_3,
            "global_3": global_3,
            "global_ok": global_ok,
            "aspects_detected": analysis.get("aspects", []),
            "aspect_results": aspect_results,
            "all_ok": global_ok and all_aspects_ok,
        })

    # Affichage
    print(f"\n  {'ID':10s} {'Cat':25s} {'Global':15s} {'Aspects':40s}")
    print("  " + "-" * 90)

    total_ok = 0
    for r in results:
        g_icon = "✅" if r["global_ok"] else "❌"
        aspects_str = ""
        for asp_name, asp_r in r["aspect_results"].items():
            a_icon = "✅" if asp_r["ok"] else "❌"
            prop = " 🔄" if asp_r["propagated"] else ""
            aspects_str += f"{a_icon}{asp_name}={asp_r['label']}{prop}  "

        if not r["aspect_results"]:
            aspects_str = "(aucun aspect)"

        print(f"  {r['id']:10s} {r['category']:25s} {g_icon}{r['global_pred']:12s} {aspects_str}")

        if any(asp_r["propagated"] for asp_r in r["aspect_results"].values()):
            for asp_name, asp_r in r["aspect_results"].items():
                if asp_r["propagated"]:
                    print(f"             → {asp_name}: local={asp_r.get('label_3','?')} → propagé={asp_r['label']} ({asp_r['reason']})")

        if r["all_ok"]:
            total_ok += 1

    print(f"\n  Résultat: {total_ok}/{len(results)} cas corrects")
    print(f"  Propagations effectuées: {sum(1 for r in results for a in r['aspect_results'].values() if a['propagated'])}")

    # Sauvegarde
    output_path = Path(model_dir).parent / "absa_test_results.json"
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)
        print(f"  Résultats sauvegardés: {output_path}")
    except Exception:
        fallback = Path("/content/absa_test_results.json")
        with open(fallback, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)
        print(f"  Résultats sauvegardés: {fallback}")


if __name__ == "__main__":
    DEFAULT_MODEL_DIR = "/content/drive/MyDrive/RamyPulse/models/dziribert-sentiment"
    model_path = DEFAULT_MODEL_DIR
    gemini_key = None

    if "--model" in sys.argv:
        idx = sys.argv.index("--model")
        model_path = sys.argv[idx + 1]

    if "--gemini-key" in sys.argv:
        idx = sys.argv.index("--gemini-key")
        gemini_key = sys.argv[idx + 1]

    run_absa_tests(model_path, gemini_key)
