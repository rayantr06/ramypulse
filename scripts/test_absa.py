"""
Test standalone du pipeline ABSA RamyPulse.

Teste :
- L'extracteur d'aspects (keyword matching)
- Le pipeline ABSA complet (aspect + sentiment par aspect)

Usage:
    python scripts/test_absa.py
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# ── Cas de test ABSA ────────────────────────────────────────────────────────
# Chaque cas indique les aspects attendus + le sentiment attendu par aspect
# Aspects RamyPulse : goût, emballage, prix, disponibilité, fraîcheur

TEST_CASES = [
    # ── GOÛT ────────────────────────────────────────────────────────────────
    {
        "id": "A01",
        "text": "طعمه زوين بزاف، bnin ومليح",
        "expected_aspects": ["goût"],
        "note": "Goût positif — Darija + Arabizi",
    },
    {
        "id": "A02",
        "text": "le goût est amer et dégoûtant, j'ai pas aimé du tout",
        "expected_aspects": ["goût"],
        "note": "Goût négatif — français pur",
    },

    # ── EMBALLAGE ───────────────────────────────────────────────────────────
    {
        "id": "A03",
        "text": "البلاستيك تاع القارورة راه يفوت في العصير، التغليف خايب",
        "expected_aspects": ["emballage"],
        "note": "Emballage négatif — bouteille/fuite",
    },
    {
        "id": "A04",
        "text": "la bouteille est bien faite, le bouchon ne fuit pas",
        "expected_aspects": ["emballage"],
        "note": "Emballage positif — français",
    },

    # ── PRIX ────────────────────────────────────────────────────────────────
    {
        "id": "A05",
        "text": "السعر غالي بزاف مقارنة بالمنافسين، ghali كثير",
        "expected_aspects": ["prix"],
        "note": "Prix négatif — Darija + Arabizi",
    },
    {
        "id": "A06",
        "text": "le prix est abordable, c'est rkhis pour la qualité",
        "expected_aspects": ["prix"],
        "note": "Prix positif — mixte",
    },

    # ── DISPONIBILITÉ ───────────────────────────────────────────────────────
    {
        "id": "A07",
        "text": "ma kaynch f les magasins, rupture de stock partout",
        "expected_aspects": ["disponibilité"],
        "note": "Disponibilité négative — Arabizi + français",
    },
    {
        "id": "A08",
        "text": "متوفر في كل المحلات والسوبرمارشي بدون مشكلة",
        "expected_aspects": ["disponibilité"],
        "note": "Disponibilité positive — arabe pur",
    },

    # ── FRAÎCHEUR ───────────────────────────────────────────────────────────
    {
        "id": "A09",
        "text": "bared et frais, j'adore quand il sort du frigo",
        "expected_aspects": ["fraîcheur"],
        "note": "Fraîcheur positive",
    },
    {
        "id": "A10",
        "text": "المنتوج مضروب، بان عليه périmé وتاريخ الانتهاء عدا",
        "expected_aspects": ["fraîcheur"],
        "note": "Fraîcheur négative — périmé/date",
    },

    # ── MULTI-ASPECTS ───────────────────────────────────────────────────────
    {
        "id": "M01",
        "text": "الطعم زوين بصح السعر غالي والتغليف خايب",
        "expected_aspects": ["goût", "prix", "emballage"],
        "note": "Multi-aspects : goût+, prix-, emballage-",
    },
    {
        "id": "M02",
        "text": "frais et bnin mais ghali et ma kaynch f les magasins",
        "expected_aspects": ["fraîcheur", "goût", "prix", "disponibilité"],
        "note": "Multi-aspects : fraîcheur+, goût+, prix-, dispo-",
    },
    {
        "id": "M03",
        "text": "ممتاز هاد المنتوج ممتاز خلاني مريض 3 يام من الطعم تاعه",
        "expected_aspects": ["goût"],
        "note": "Sarcasme goût — طعم mentionné + مريض",
    },

    # ── AUCUN ASPECT ────────────────────────────────────────────────────────
    {
        "id": "Z01",
        "text": "برافو عليهم يبيعوا ماء الصرف الصحي",
        "expected_aspects": [],
        "note": "Aucun aspect métier — commentaire général",
    },
    {
        "id": "Z02",
        "text": "Ramy c'est une marque algérienne depuis longtemps",
        "expected_aspects": [],
        "note": "Aucun aspect — fait général",
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# Affichage
# ─────────────────────────────────────────────────────────────────────────────

SENTIMENT_ICON = {
    "positif": "✅",
    "négatif": "❌",
    "neutre":  "⚪",
    "positive": "✅",
    "negative": "❌",
    "neutral":  "⚪",
    "très_positif": "✅✅",
    "très_négatif": "❌❌",
    "mixte": "🔀",
}

def _aspect_verdict(detected: list[str], expected: list[str]) -> str:
    det = set(detected)
    exp = set(expected)
    if det == exp:
        return "✓ CORRECT"
    missing = exp - det
    extra   = det - exp
    parts = []
    if missing:
        parts.append(f"manquants:{missing}")
    if extra:
        parts.append(f"en_trop:{extra}")
    return "✗ " + " / ".join(parts)


def print_absa_result(case: dict, result: dict) -> None:
    detected_aspects = result.get("aspects", [])
    global_sent = result.get("global_sentiment", "?")
    global_conf = result.get("confidence", 0)
    aspect_sents = result.get("aspect_sentiments", [])

    verdict = _aspect_verdict(detected_aspects, case["expected_aspects"])

    print(f"\n{'─'*65}")
    print(f"[{case['id']}] {case['note']}")
    print(f"Texte    : {case['text'][:80]}")
    print(f"─" * 40)
    print(f"Global   : {SENTIMENT_ICON.get(global_sent, '?')} {global_sent} ({global_conf:.1%})")
    print(f"Aspects  : {detected_aspects if detected_aspects else '(aucun)'}")
    print(f"Verdict  : {verdict}")

    if aspect_sents:
        print("Détail par aspect :")
        for a in aspect_sents:
            icon = SENTIMENT_ICON.get(str(a.get("sentiment", "")), "?")
            print(f"  [{a['aspect']:15s}] mention=«{a['mention'][:20]}» → {icon} {a['sentiment']} ({a.get('confidence', 0):.1%})")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 65)
    print("   TEST ABSA RamyPulse")
    print("=" * 65)
    print(f"Aspects configurés : goût | emballage | prix | disponibilité | fraîcheur")
    print(f"Cas de test : {len(TEST_CASES)}")

    # ── Charger ABSA ────────────────────────────────────────────────────────
    print("\nChargement du pipeline ABSA...")
    from core.analysis.absa_engine import analyze_text
    print("Pipeline chargé.\n")

    # ── Phase 1 : Extracteur d'aspects seul ─────────────────────────────────
    print("=" * 65)
    print("  PHASE 1 — Extracteur d'aspects (keyword matching)")
    print("=" * 65)

    from core.analysis.aspect_extractor import extract_aspects

    aspect_correct = 0
    for case in TEST_CASES:
        mentions = extract_aspects(case["text"])
        detected = list(dict.fromkeys(m["aspect"] for m in mentions))  # ordre préservé, unique
        exp = case["expected_aspects"]
        ok = set(detected) == set(exp)
        if ok:
            aspect_correct += 1
        status = "✓" if ok else "✗"
        missing = set(exp) - set(detected)
        extra   = set(detected) - set(exp)
        detail = ""
        if missing:
            detail += f" | manquants:{missing}"
        if extra:
            detail += f" | en_trop:{extra}"
        print(f"  [{case['id']}] {status}  {case['note'][:50]:50s} → {detected}{detail}")

    print(f"\n→ Extracteur : {aspect_correct}/{len(TEST_CASES)} corrects")

    # ── Phase 2 : ABSA complet (aspects + sentiment par aspect) ─────────────
    print("\n" + "=" * 65)
    print("  PHASE 2 — ABSA complet (aspects + sentiment par aspect)")
    print("=" * 65)

    absa_correct = 0
    for case in TEST_CASES:
        result = analyze_text(case["text"])
        detected = result.get("aspects", [])
        if set(detected) == set(case["expected_aspects"]):
            absa_correct += 1
        print_absa_result(case, result)

    print(f"\n→ ABSA complet : {absa_correct}/{len(TEST_CASES)} aspects corrects")

    # ── Récap ────────────────────────────────────────────────────────────────
    print("\n" + "=" * 65)
    print("  RÉCAPITULATIF")
    print("=" * 65)
    print(f"Extracteur aspects   : {aspect_correct}/{len(TEST_CASES)} ({aspect_correct/len(TEST_CASES):.0%})")
    print(f"ABSA full pipeline   : {absa_correct}/{len(TEST_CASES)} ({absa_correct/len(TEST_CASES):.0%})")
    print("=" * 65)


if __name__ == "__main__":
    main()
