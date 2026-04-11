#!/usr/bin/env python3
"""
reannotate_logprobs.py — Ré-annotation avec soft labels calibrées
==================================================================

Génère de VRAIES soft labels via Monte Carlo sampling :
- Chaque commentaire est classifié N fois (défaut: 30) avec température > 0
- La distribution empirique des votes = soft labels calibrées
- Un commentaire ambigu aura des votes répartis (ex: pos=0.4 neg=0.1 neu=0.5)
- Un commentaire clair aura des votes unanimes (ex: neg=1.0)

Usage :
    python reannotate_logprobs.py \\
        --input annotated_comments.json \\
        --output reannotated_soft.csv \\
        --model gemini-3.1-pro-preview \\
        --api-key VOTRE_CLE \\
        --passes 30

Le script est INCRÉMENTAL : s'il est interrompu, relancez-le avec les mêmes
arguments — il reprend là où il s'est arrêté.

Dépendances : pip install google-genai pandas
"""

import argparse
import json
import math
import os
import sys
import time
from collections import Counter
from pathlib import Path

import pandas as pd

# ── Configuration ────────────────────────────────────────────────────────────

VALID_LABELS = {"positive", "negative", "neutral"}

PROMPT_TEMPLATE = """Tu es un annotateur expert en analyse de sentiment pour les avis clients algériens.
Les commentaires sont en Derja (dialecte algérien), Arabizi, français, arabe standard, ou un mélange.

Classifie ce commentaire en UN SEUL MOT parmi : positive, negative, neutral

Règles :
- positive = le client exprime de la satisfaction, un compliment, de l'enthousiasme pour le produit
- negative = le client exprime une plainte, une critique, un mécontentement envers le produit
- neutral = question, mention factuelle, tag de personne, participation à un concours, hors sujet

Commentaire : {text}

Classe :"""


# ── Fonctions ────────────────────────────────────────────────────────────────

def parse_label(raw_text: str) -> str | None:
    """Extrait le label depuis la réponse brute du LLM."""
    if not raw_text:
        return None
    # Prendre le premier mot, nettoyer
    word = raw_text.strip().lower().split()[0].rstrip(".,;:!?")
    # Mapper les variantes
    if "positiv" in word or "positif" in word:
        return "positive"
    elif "negativ" in word or "négatif" in word or "negatif" in word:
        return "negative"
    elif "neutr" in word:
        return "neutral"
    return None


def annotate_one(client, model: str, text: str, n_passes: int,
                 temperature: float, delay: float) -> dict:
    """
    Annote un commentaire via Monte Carlo sampling.

    Retourne :
        {
            "votes": {"positive": 5, "negative": 22, "neutral": 3},
            "valid_passes": 30,
            "soft_positive": 0.167,
            "soft_negative": 0.733,
            "soft_neutral": 0.100,
            "hard_label": "negative",
            "confidence": 0.733,
            "entropy": 1.05,
        }
    """
    from google.genai import types

    votes = Counter()
    errors = 0

    prompt = PROMPT_TEMPLATE.format(text=text[:500])  # Tronquer les très longs

    for i in range(n_passes):
        try:
            resp = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=15,
                ),
            )
            raw = resp.text
            label = parse_label(raw) if raw else None
            if label:
                votes[label] += 1
            else:
                errors += 1
        except Exception as e:
            errors += 1
            err_msg = str(e)
            # Rate limit → attendre plus longtemps
            if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                wait = 30
                print(f"      Rate limit — pause {wait}s...")
                time.sleep(wait)
            elif "500" in err_msg or "503" in err_msg:
                time.sleep(5)

        if delay > 0:
            time.sleep(delay)

    # Calculer les soft labels
    valid = sum(votes.values())
    if valid == 0:
        return {
            "votes": dict(votes), "valid_passes": 0, "errors": errors,
            "soft_positive": 0, "soft_negative": 0, "soft_neutral": 0,
            "hard_label": "neutral", "confidence": 0, "entropy": 0,
        }

    probs = {lab: votes.get(lab, 0) / valid for lab in VALID_LABELS}
    hard_label = max(probs, key=probs.get)
    confidence = probs[hard_label]

    # Shannon entropy (0 = certain, log2(3) ≈ 1.58 = max uncertainty)
    entropy = -sum(p * math.log2(p + 1e-10) for p in probs.values() if p > 0)

    return {
        "votes": dict(votes),
        "valid_passes": valid,
        "errors": errors,
        "soft_positive": round(probs["positive"], 4),
        "soft_negative": round(probs["negative"], 4),
        "soft_neutral": round(probs["neutral"], 4),
        "hard_label": hard_label,
        "confidence": round(confidence, 4),
        "entropy": round(entropy, 4),
    }


def load_progress(output_path: str) -> set:
    """Charge les indices déjà annotés (pour reprise incrémentale)."""
    if not os.path.exists(output_path):
        return set()
    df = pd.read_csv(output_path)
    return set(df["index"].tolist())


def save_row(output_path: str, row: dict, write_header: bool):
    """Sauvegarde une ligne dans le CSV (append)."""
    df = pd.DataFrame([row])
    df.to_csv(output_path, mode="a", header=write_header, index=False)


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Ré-annote avec soft labels calibrées via Monte Carlo sampling"
    )
    parser.add_argument("--input", "-i", required=True,
                        help="Fichier JSON annoté (annotated_comments.json)")
    parser.add_argument("--output", "-o", default="reannotated_soft.csv",
                        help="CSV de sortie (défaut: reannotated_soft.csv)")
    parser.add_argument("--model", "-m", default="gemini-3.1-pro-preview",
                        help="Modèle Gemini (défaut: gemini-3.1-pro-preview)")
    parser.add_argument("--api-key", "-k", required=True,
                        help="Clé API Gemini")
    parser.add_argument("--passes", "-n", type=int, default=30,
                        help="Nombre de passes par commentaire (défaut: 30)")
    parser.add_argument("--temperature", "-t", type=float, default=1.5,
                        help="Température de sampling (défaut: 1.5)")
    parser.add_argument("--delay", "-d", type=float, default=0.15,
                        help="Délai entre les appels API en secondes (défaut: 0.15)")
    parser.add_argument("--start", type=int, default=0,
                        help="Index de départ (défaut: 0)")
    parser.add_argument("--limit", type=int, default=None,
                        help="Nombre max de commentaires à traiter")

    args = parser.parse_args()

    # Charger les données
    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"Chargé : {len(data)} commentaires depuis {args.input}")

    # Initialiser le client Gemini
    from google import genai
    client = genai.Client(api_key=args.api_key)

    # Vérifier la connexion avec un test rapide
    print(f"Modèle : {args.model}")
    print(f"Passes : {args.passes} par commentaire (T={args.temperature})")
    try:
        test_resp = client.models.generate_content(
            model=args.model,
            contents="Réponds juste 'ok'.",
            config=genai.types.GenerateContentConfig(
                temperature=0, max_output_tokens=5,
            ),
        )
        test_text = test_resp.text or ""
        print(f"Test API : '{test_text.strip()}' ✓")
    except Exception as e:
        print(f"Erreur API : {e}")
        print("Vérifie ta clé API et le nom du modèle.")
        sys.exit(1)

    # Charger la progression
    done_indices = load_progress(args.output)
    write_header = len(done_indices) == 0
    print(f"Déjà annotés : {len(done_indices)}")

    # Déterminer la plage
    end = len(data) if args.limit is None else min(args.start + args.limit, len(data))
    to_process = [(i, data[i]) for i in range(args.start, end) if i not in done_indices]
    print(f"À traiter : {len(to_process)} commentaires")

    if not to_process:
        print("Rien à faire !")
        return

    # Estimer le temps
    est_per_comment = args.passes * (args.delay + 0.5)  # ~0.5s par appel API
    est_total = len(to_process) * est_per_comment / 60
    print(f"Temps estimé : ~{est_total:.0f} min ({est_per_comment:.0f}s/commentaire)")
    print(f"Appels API total : ~{len(to_process) * args.passes:,}")
    print()

    # ── Boucle d'annotation ──
    t_start = time.time()
    success = 0
    low_quality = 0

    for batch_idx, (idx, item) in enumerate(to_process):
        text = item["text"]
        orig_label = item.get("sentiment", "")

        result = annotate_one(
            client=client,
            model=args.model,
            text=text,
            n_passes=args.passes,
            temperature=args.temperature,
            delay=args.delay,
        )

        # Construire la ligne CSV
        row = {
            "index": idx,
            "text": text,
            "hard_label": result["hard_label"],
            "hard_label_original": orig_label,
            "confidence": result["confidence"],
            "soft_positive": result["soft_positive"],
            "soft_negative": result["soft_negative"],
            "soft_neutral": result["soft_neutral"],
            "entropy": result["entropy"],
            "valid_passes": result["valid_passes"],
            "errors": result["errors"],
            "votes_positive": result["votes"].get("positive", 0),
            "votes_negative": result["votes"].get("negative", 0),
            "votes_neutral": result["votes"].get("neutral", 0),
            "brand": item.get("brand", ""),
            "post_url": item.get("post_url", ""),
        }

        save_row(args.output, row, write_header=(write_header and batch_idx == 0))
        success += 1

        # Qualité check
        if result["valid_passes"] < args.passes * 0.5:
            low_quality += 1

        # Logging
        elapsed = time.time() - t_start
        rate = success / (elapsed / 60) if elapsed > 0 else 0
        label_changed = "→" if result["hard_label"] != orig_label else "="

        if (batch_idx + 1) % 10 == 0 or batch_idx == 0:
            print(
                f"  [{batch_idx+1:4d}/{len(to_process)}] "
                f"idx={idx:4d} | {orig_label:8s} {label_changed} {result['hard_label']:8s} | "
                f"conf={result['confidence']:.2f} ent={result['entropy']:.2f} | "
                f"votes=p{result['votes'].get('positive',0)}/n{result['votes'].get('negative',0)}/u{result['votes'].get('neutral',0)} | "
                f"{rate:.1f}/min"
            )

    # ── Résumé final ──
    elapsed = time.time() - t_start
    print(f"\n{'='*65}")
    print(f"  TERMINÉ — {success} commentaires ré-annotés en {elapsed/60:.1f} min")
    print(f"  Fichier : {args.output}")
    print(f"  Low quality (< 50% valid) : {low_quality}")
    print(f"{'='*65}")

    # Stats sur le CSV final
    if os.path.exists(args.output):
        df = pd.read_csv(args.output)
        print(f"\n  Total dans le CSV : {len(df)}")
        print(f"  Distribution labels durs :")
        print(df["hard_label"].value_counts().to_string())
        print(f"\n  Entropie moyenne : {df['entropy'].mean():.3f}")
        print(f"  Commentaires ambigus (entropy > 0.5) : {(df['entropy'] > 0.5).sum()}")
        print(f"  Labels changés vs original : {(df['hard_label'] != df['hard_label_original']).sum()}")

        # Soft label stats
        print(f"\n  Soft labels — stats :")
        for col in ["soft_positive", "soft_negative", "soft_neutral"]:
            vals = df[col]
            n_unique = vals.nunique()
            print(f"    {col:15s} : mean={vals.mean():.3f}, std={vals.std():.3f}, unique={n_unique}")


if __name__ == "__main__":
    main()
