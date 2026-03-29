"""Script CLI d'évaluation du classifieur de sentiment RamyPulse.

Usage :
    python scripts/evaluate_classifier.py --dataset data/test_set.parquet --output reports/eval.json

Retourne exit code 0 si les critères Phase 0 sont atteints, 1 sinon.
"""
import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

# Ajouter le répertoire racine au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import SENTIMENT_LABELS  # noqa: E402
from core.analysis.evaluation import ClassifierEvaluator  # noqa: E402
from core.analysis.sentiment_classifier import SentimentClassifier  # noqa: E402

logger = logging.getLogger(__name__)


def main() -> int:
    """Point d'entrée principal du script d'évaluation.

    Returns:
        0 si critères Phase 0 atteints, 1 sinon.
    """
    parser = argparse.ArgumentParser(
        description="Évalue le classifieur de sentiment RamyPulse sur un dataset annoté."
    )
    parser.add_argument(
        "--dataset",
        required=True,
        help="Chemin vers le dataset Parquet (colonnes: text, sentiment_label)",
    )
    parser.add_argument(
        "--output",
        default="reports/eval_report.json",
        help="Chemin du rapport JSON de sortie (défaut: reports/eval_report.json)",
    )
    args = parser.parse_args()

    # Configuration logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Charger le dataset
    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        logger.error("Dataset introuvable : %s", dataset_path)
        return 1

    logger.info("Chargement du dataset : %s", dataset_path)
    df = pd.read_parquet(dataset_path)

    required_cols = {"text", "sentiment_label"}
    if not required_cols.issubset(df.columns):
        logger.error(
            "Colonnes manquantes. Requises : %s, Trouvées : %s",
            required_cols, set(df.columns),
        )
        return 1

    dataset = df[["text", "sentiment_label"]].to_dict(orient="records")
    logger.info("Dataset chargé : %d exemples", len(dataset))

    # Instancier le classifieur
    logger.info("Chargement du classifieur...")
    classifier = SentimentClassifier()

    # Évaluer
    evaluator = ClassifierEvaluator(labels=SENTIMENT_LABELS)
    report = evaluator.evaluate_from_dataset(classifier, dataset)

    # Afficher le rapport markdown
    logger.info("\n%s", report.to_markdown())

    # Sauvegarder le rapport JSON
    report.save(args.output)
    logger.info("Rapport sauvegardé : %s", args.output)

    # Vérifier les critères Phase 0
    if report.meets_phase0_criteria():
        logger.info("✅ Critères Phase 0 ATTEINTS — le modèle est validé.")
        return 0
    else:
        logger.warning(
            "❌ Critères Phase 0 NON ATTEINTS — F1 macro=%.4f, Accuracy=%.4f",
            report.f1_macro, report.accuracy,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
