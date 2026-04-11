#!/usr/bin/env python3
"""
prepare_dataset.py — Préparation du dataset pour le fine-tuning DziriBERT
=========================================================================

Ce script effectue :
1. Fusion de la classe "mixed" dans les 3 classes principales (positive/negative/neutral)
   en utilisant les soft labels (probabilités) du LLM annotateur.
2. Calcul des class weights (inverse frequency) pour la loss pondérée.
3. Split stratifié train/val/test (70/15/15).
4. Export en CSV + fichier JSON de config (class weights, label mapping, stats).

Usage :
    python prepare_dataset.py --input <annotated_comments.json> --output-dir <output_dir>

Dépendances : pandas, scikit-learn (pip install pandas scikit-learn)
"""

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split


# ── Configuration ────────────────────────────────────────────────────────────

LABEL2ID = {"positive": 0, "negative": 1, "neutral": 2}
ID2LABEL = {v: k for k, v in LABEL2ID.items()}
SOFT_KEY_MAP = {"pos": "positive", "neg": "negative", "neu": "neutral", "mix": None}
RANDOM_SEED = 42


# ── Fonctions ────────────────────────────────────────────────────────────────

def load_annotated(path: str) -> list[dict]:
    """Charge le fichier JSON annoté."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"  Chargé : {len(data)} commentaires depuis {path}")
    return data


def fuse_mixed(data: list[dict]) -> list[dict]:
    """
    Redistribue les exemples 'mixed' dans la classe la plus probable
    selon les soft labels du LLM (candidates.pos / neg / neu).

    Logique :
    - Pour chaque exemple mixed, on regarde les probabilités pos/neg/neu
    - On assigne la classe avec la probabilité la plus élevée
    - Si toutes les probas sont égales (rare), on assigne 'neutral'
    """
    fused = []
    reassignment_counts = Counter()
    mixed_count = 0

    for item in data:
        if item.get("sentiment") != "mixed":
            fused.append(item)
            continue

        mixed_count += 1
        candidates = item.get("candidates", {})

        # Extraire les scores des 3 classes cibles
        scores = {
            "positive": candidates.get("pos", 0),
            "negative": candidates.get("neg", 0),
            "neutral":  candidates.get("neu", 0),
        }

        # Classe avec la probabilité la plus élevée
        new_label = max(scores, key=scores.get)

        # En cas d'égalité parfaite, fallback neutral
        max_score = scores[new_label]
        ties = [k for k, v in scores.items() if v == max_score]
        if len(ties) > 1:
            new_label = "neutral"

        # Créer une copie modifiée
        new_item = item.copy()
        new_item["sentiment_original"] = "mixed"
        new_item["sentiment"] = new_label

        # Mettre à jour la confiance avec le score de la nouvelle classe
        new_item["confidence"] = scores[new_label]

        fused.append(new_item)
        reassignment_counts[new_label] += 1

    print(f"\n  Fusion 'mixed' → 3 classes :")
    print(f"    Total mixed trouvés : {mixed_count}")
    for label, count in reassignment_counts.most_common():
        print(f"    mixed → {label} : {count}")

    return fused


def compute_class_weights(labels: list[str]) -> dict[str, float]:
    """
    Calcule les class weights (inverse frequency normalisé).

    Formule : w_c = N_total / (N_classes * N_c)
    C'est la même formule que sklearn.utils.class_weight.compute_class_weight('balanced').
    """
    counts = Counter(labels)
    n_total = len(labels)
    n_classes = len(counts)

    weights = {}
    for label, count in counts.items():
        weights[label] = n_total / (n_classes * count)

    return weights


def compute_focal_alpha(labels: list[str]) -> dict[str, float]:
    """
    Calcule alpha pour Focal Loss = 1 - fréquence relative de chaque classe.
    Les classes rares obtiennent un alpha plus élevé.
    """
    counts = Counter(labels)
    n_total = len(labels)

    alpha = {}
    for label, count in counts.items():
        alpha[label] = 1.0 - (count / n_total)

    return alpha


def stratified_split(
    df: pd.DataFrame,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    seed: int = RANDOM_SEED,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Split stratifié en 3 ensembles."""
    assert abs(train_ratio + val_ratio + test_ratio - 1.0) < 1e-6

    # Premier split : train vs (val + test)
    train_df, temp_df = train_test_split(
        df,
        test_size=(val_ratio + test_ratio),
        stratify=df["label"],
        random_state=seed,
    )

    # Second split : val vs test
    relative_test = test_ratio / (val_ratio + test_ratio)
    val_df, test_df = train_test_split(
        temp_df,
        test_size=relative_test,
        stratify=temp_df["label"],
        random_state=seed,
    )

    return train_df, val_df, test_df


def build_final_dataframe(data: list[dict]) -> pd.DataFrame:
    """Construit le DataFrame final avec les colonnes nécessaires au fine-tuning."""
    records = []
    for item in data:
        sentiment = item["sentiment"]
        if sentiment not in LABEL2ID:
            continue  # skip si label inconnu

        records.append({
            "text": item["text"],
            "label": sentiment,
            "label_id": LABEL2ID[sentiment],
            "confidence": item.get("confidence", 0.0),
            "prob_positive": item.get("candidates", {}).get("pos", 0.0),
            "prob_negative": item.get("candidates", {}).get("neg", 0.0),
            "prob_neutral": item.get("candidates", {}).get("neu", 0.0),
            "brand": item.get("brand", ""),
            "was_mixed": item.get("sentiment_original") == "mixed",
        })

    return pd.DataFrame(records)


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Prépare le dataset 3-classes pour le fine-tuning DziriBERT"
    )
    parser.add_argument(
        "--input", "-i",
        default="annotated_comments.json",
        help="Fichier JSON annoté (défaut: annotated_comments.json)",
    )
    parser.add_argument(
        "--output-dir", "-o",
        default=".",
        help="Dossier de sortie (défaut: répertoire courant)",
    )
    parser.add_argument(
        "--train-ratio", type=float, default=0.70,
        help="Ratio du split train (défaut: 0.70)",
    )
    parser.add_argument(
        "--val-ratio", type=float, default=0.15,
        help="Ratio du split validation (défaut: 0.15)",
    )
    parser.add_argument(
        "--test-ratio", type=float, default=0.15,
        help="Ratio du split test (défaut: 0.15)",
    )
    parser.add_argument(
        "--seed", type=int, default=RANDOM_SEED,
        help="Random seed (défaut: 42)",
    )

    args = parser.parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 65)
    print("  PRÉPARATION DU DATASET — DziriBERT Sentiment (3 classes)")
    print("=" * 65)

    # 1. Charger les données annotées
    print("\n[1/5] Chargement des données annotées...")
    data = load_annotated(args.input)

    # Distribution originale
    original_counts = Counter(d["sentiment"] for d in data)
    print("\n  Distribution originale :")
    for label in ["neutral", "positive", "negative", "mixed"]:
        c = original_counts.get(label, 0)
        print(f"    {label:10s} : {c:4d} ({c/len(data)*100:.1f}%)")

    # 2. Fusionner les mixed
    print("\n[2/5] Fusion de la classe 'mixed'...")
    data = fuse_mixed(data)

    # 3. Construire le DataFrame
    print("\n[3/5] Construction du DataFrame final...")
    df = build_final_dataframe(data)
    print(f"  Total exemples : {len(df)}")

    final_counts = Counter(df["label"])
    print("\n  Distribution après fusion :")
    for label in ["neutral", "positive", "negative"]:
        c = final_counts.get(label, 0)
        print(f"    {label:10s} : {c:4d} ({c/len(df)*100:.1f}%)")

    was_mixed = df["was_mixed"].sum()
    print(f"  Exemples redistribués depuis 'mixed' : {was_mixed}")

    # 4. Calculer les class weights
    print("\n[4/5] Calcul des class weights et focal alpha...")
    labels_list = df["label"].tolist()
    class_weights = compute_class_weights(labels_list)
    focal_alpha = compute_focal_alpha(labels_list)

    print("\n  Class weights (inverse frequency) :")
    for label in ["neutral", "positive", "negative"]:
        print(f"    weight_{label:10s} = {class_weights[label]:.4f}")

    print("\n  Focal loss alpha :")
    for label in ["neutral", "positive", "negative"]:
        print(f"    alpha_{label:10s} = {focal_alpha[label]:.4f}")

    # 5. Split stratifié
    print("\n[5/5] Split stratifié train/val/test...")
    train_df, val_df, test_df = stratified_split(
        df,
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
        test_ratio=args.test_ratio,
        seed=args.seed,
    )

    print(f"  Train : {len(train_df):4d} exemples")
    print(f"  Val   : {len(val_df):4d} exemples")
    print(f"  Test  : {len(test_df):4d} exemples")

    # Vérifier la stratification
    for name, split_df in [("train", train_df), ("val", val_df), ("test", test_df)]:
        split_counts = Counter(split_df["label"])
        pcts = {l: split_counts.get(l, 0) / len(split_df) * 100 for l in LABEL2ID}
        print(f"    {name:5s} → " + " | ".join(f"{l}: {pcts[l]:.0f}%" for l in LABEL2ID))

    # ── Export ───────────────────────────────────────────────────────────────

    # CSV splits (colonnes : text, label, label_id)
    cols_export = ["text", "label", "label_id"]
    train_df[cols_export].to_csv(output_dir / "train.csv", index=False)
    val_df[cols_export].to_csv(output_dir / "val.csv", index=False)
    test_df[cols_export].to_csv(output_dir / "test.csv", index=False)

    # CSV complet avec métadonnées
    df.to_csv(output_dir / "dataset_3classes_full.csv", index=False)

    # Config JSON
    config = {
        "task": "sentiment_classification",
        "num_labels": 3,
        "label2id": LABEL2ID,
        "id2label": ID2LABEL,
        "class_weights": {label: round(w, 4) for label, w in class_weights.items()},
        "class_weights_tensor_order": [
            round(class_weights[ID2LABEL[i]], 4) for i in range(3)
        ],
        "focal_alpha": {label: round(a, 4) for label, a in focal_alpha.items()},
        "focal_alpha_tensor_order": [
            round(focal_alpha[ID2LABEL[i]], 4) for i in range(3)
        ],
        "dataset_stats": {
            "total": len(df),
            "train": len(train_df),
            "val": len(val_df),
            "test": len(test_df),
            "distribution": {
                label: final_counts.get(label, 0) for label in LABEL2ID
            },
            "mixed_redistributed": int(was_mixed),
        },
        "split_ratios": {
            "train": args.train_ratio,
            "val": args.val_ratio,
            "test": args.test_ratio,
        },
        "random_seed": args.seed,
        "model": "alger-ia/dziribert",
        "max_seq_length": 128,
    }

    config_path = output_dir / "training_config.json"
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print(f"\n  Fichiers exportés dans {output_dir}/ :")
    print(f"    train.csv                ({len(train_df)} lignes)")
    print(f"    val.csv                  ({len(val_df)} lignes)")
    print(f"    test.csv                 ({len(test_df)} lignes)")
    print(f"    dataset_3classes_full.csv ({len(df)} lignes)")
    print(f"    training_config.json     (class weights + metadata)")

    print("\n" + "=" * 65)
    print("  TERMINÉ — Dataset prêt pour le fine-tuning DziriBERT")
    print("=" * 65)

    return config


if __name__ == "__main__":
    main()
