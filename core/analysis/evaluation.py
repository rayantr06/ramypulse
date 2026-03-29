"""Framework d'évaluation continue du classifieur de sentiment RamyPulse.

Fournit :
- ClassifierEvaluator : calcul de F1, accuracy, matrice de confusion
- EvaluationReport : rapport structuré avec sérialisation JSON/markdown
- compare_reports : delta entre deux évaluations (avant/après fine-tuning)

Compatible avec et sans sklearn. Utilise sklearn si disponible, sinon
implémentation manuelle des métriques.
"""
from __future__ import annotations

import json
import logging
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

# Tenter d'importer sklearn pour les métriques optimisées
_HAS_SKLEARN = False
try:
    from sklearn.metrics import (
        accuracy_score,
        confusion_matrix as sk_confusion_matrix,
        f1_score,
        precision_score,
        recall_score,
    )
    _HAS_SKLEARN = True
    logger.debug("sklearn disponible — métriques optimisées activées.")
except ImportError:
    logger.debug("sklearn indisponible — métriques calculées manuellement.")


# ---------------------------------------------------------------------------
# Seuils Phase 0 (PRD §23.1)
# ---------------------------------------------------------------------------

_PHASE0_F1_MACRO_MIN = 0.70
_PHASE0_F1_PER_CLASS_MIN = 0.60
_PHASE0_ACCURACY_MIN = 0.65


# ---------------------------------------------------------------------------
# Implémentation manuelle des métriques (fallback sans sklearn)
# ---------------------------------------------------------------------------

def _manual_accuracy(y_true: list[str], y_pred: list[str]) -> float:
    """Calcule l'accuracy manuellement."""
    if not y_true:
        return 0.0
    correct = sum(1 for t, p in zip(y_true, y_pred) if t == p)
    return correct / len(y_true)


def _manual_confusion_matrix(y_true: list[str], y_pred: list[str],
                              labels: list[str]) -> list[list[int]]:
    """Calcule la matrice de confusion manuellement."""
    label_to_idx = {label: i for i, label in enumerate(labels)}
    n = len(labels)
    matrix = [[0] * n for _ in range(n)]
    for t, p in zip(y_true, y_pred):
        ti = label_to_idx.get(t)
        pi = label_to_idx.get(p)
        if ti is not None and pi is not None:
            matrix[ti][pi] += 1
    return matrix


def _manual_f1_per_class(y_true: list[str], y_pred: list[str],
                          labels: list[str]) -> dict[str, float]:
    """Calcule le F1-score par classe manuellement."""
    result = {}
    for label in labels:
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == label and p == label)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t != label and p == label)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == label and p != label)
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall / (precision + recall)
              if (precision + recall) > 0 else 0.0)
        result[label] = round(f1, 6)
    return result


def _manual_precision_macro(y_true: list[str], y_pred: list[str],
                             labels: list[str]) -> float:
    """Calcule la précision macro manuellement."""
    precisions = []
    for label in labels:
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == label and p == label)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t != label and p == label)
        precisions.append(tp / (tp + fp) if (tp + fp) > 0 else 0.0)
    return sum(precisions) / len(precisions) if precisions else 0.0


def _manual_recall_macro(y_true: list[str], y_pred: list[str],
                          labels: list[str]) -> float:
    """Calcule le rappel macro manuellement."""
    recalls = []
    for label in labels:
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == label and p == label)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == label and p != label)
        recalls.append(tp / (tp + fn) if (tp + fn) > 0 else 0.0)
    return sum(recalls) / len(recalls) if recalls else 0.0


# ---------------------------------------------------------------------------
# EvaluationReport
# ---------------------------------------------------------------------------

@dataclass
class EvaluationReport:
    """Rapport d'évaluation complet du classifieur de sentiment."""

    accuracy: float
    f1_macro: float
    f1_per_class: dict[str, float]
    precision_macro: float
    recall_macro: float
    confusion_matrix: list[list[int]]
    labels: list[str]
    n_samples: int
    timestamp: str

    def meets_phase0_criteria(self) -> bool:
        """Vérifie si les critères de sortie Phase 0 du PRD §23.1 sont atteints.

        Critères :
        - F1 macro ≥ 0.70
        - F1 par classe ≥ 0.60 pour chaque classe
        - Accuracy ≥ 0.65

        Returns:
            True si tous les critères sont satisfaits.
        """
        if self.f1_macro < _PHASE0_F1_MACRO_MIN:
            return False
        if self.accuracy < _PHASE0_ACCURACY_MIN:
            return False
        for label, f1 in self.f1_per_class.items():
            if f1 < _PHASE0_F1_PER_CLASS_MIN:
                return False
        return True

    def to_dict(self) -> dict:
        """Sérialise le rapport en dict JSON-compatible."""
        return asdict(self)

    def to_markdown(self) -> str:
        """Génère un rapport lisible en markdown avec tableau et matrice de confusion.

        Returns:
            Chaîne markdown formatée.
        """
        lines = []
        lines.append("# Rapport d'évaluation du classifieur")
        lines.append("")
        lines.append(f"**Date :** {self.timestamp}")
        lines.append(f"**Échantillons :** {self.n_samples}")
        lines.append("")

        # Critères Phase 0
        passed = self.meets_phase0_criteria()
        status = "✅ ATTEINTS" if passed else "❌ NON ATTEINTS"
        lines.append(f"## Critères Phase 0 : {status}")
        lines.append("")
        lines.append("| Critère | Seuil | Valeur | Statut |")
        lines.append("|---------|-------|--------|--------|")
        lines.append(
            f"| F1 macro | ≥ {_PHASE0_F1_MACRO_MIN:.2f} "
            f"| {self.f1_macro:.4f} "
            f"| {'✅' if self.f1_macro >= _PHASE0_F1_MACRO_MIN else '❌'} |"
        )
        lines.append(
            f"| Accuracy | ≥ {_PHASE0_ACCURACY_MIN:.2f} "
            f"| {self.accuracy:.4f} "
            f"| {'✅' if self.accuracy >= _PHASE0_ACCURACY_MIN else '❌'} |"
        )
        lines.append("")

        # F1 par classe
        lines.append("## F1 par classe")
        lines.append("")
        lines.append("| Classe | F1 | Seuil | Statut |")
        lines.append("|--------|----|----- -|--------|")
        for label in self.labels:
            f1 = self.f1_per_class.get(label, 0.0)
            ok = f1 >= _PHASE0_F1_PER_CLASS_MIN
            lines.append(
                f"| {label} | {f1:.4f} "
                f"| ≥ {_PHASE0_F1_PER_CLASS_MIN:.2f} "
                f"| {'✅' if ok else '❌'} |"
            )
        lines.append("")

        # Métriques globales
        lines.append("## Métriques globales")
        lines.append("")
        lines.append("| Métrique | Valeur |")
        lines.append("|----------|--------|")
        lines.append(f"| Accuracy | {self.accuracy:.4f} |")
        lines.append(f"| F1 macro | {self.f1_macro:.4f} |")
        lines.append(f"| Precision macro | {self.precision_macro:.4f} |")
        lines.append(f"| Recall macro | {self.recall_macro:.4f} |")
        lines.append("")

        # Matrice de confusion
        lines.append("## Matrice de confusion")
        lines.append("")
        header = "| | " + " | ".join(self.labels) + " |"
        lines.append(header)
        lines.append("|" + "---|" * (len(self.labels) + 1))
        for i, label in enumerate(self.labels):
            row_vals = " | ".join(str(v) for v in self.confusion_matrix[i])
            lines.append(f"| **{label}** | {row_vals} |")
        lines.append("")

        return "\n".join(lines)

    def save(self, path: str) -> None:
        """Sauvegarde le rapport en JSON.

        Args:
            path: Chemin du fichier JSON de sortie.
        """
        parent = Path(path).parent
        parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, ensure_ascii=False, indent=2)
        logger.info("Rapport d'évaluation sauvegardé : %s", path)

    @classmethod
    def load(cls, path: str) -> "EvaluationReport":
        """Charge un rapport depuis un fichier JSON.

        Args:
            path: Chemin du fichier JSON.

        Returns:
            Instance EvaluationReport reconstituée.
        """
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        logger.info("Rapport d'évaluation chargé : %s", path)
        return cls(**data)


# ---------------------------------------------------------------------------
# ClassifierEvaluator
# ---------------------------------------------------------------------------

class ClassifierEvaluator:
    """Évaluateur du classifieur de sentiment RamyPulse.

    Calcule F1 macro, F1 par classe, accuracy, precision, recall,
    et matrice de confusion. Compatible avec et sans sklearn.
    """

    def __init__(self, labels: list[str] | None = None) -> None:
        """Initialise l'évaluateur avec les labels de classification.

        Args:
            labels: Liste ordonnée des classes. Si None, utilise SENTIMENT_LABELS.
        """
        if labels is None:
            from config import SENTIMENT_LABELS
            self.labels = list(SENTIMENT_LABELS)
        else:
            self.labels = list(labels)

    def evaluate(self, y_true: list[str], y_pred: list[str]) -> EvaluationReport:
        """Évalue les prédictions par rapport aux vraies étiquettes.

        Args:
            y_true: Étiquettes réelles.
            y_pred: Étiquettes prédites.

        Returns:
            EvaluationReport avec toutes les métriques.

        Raises:
            ValueError: Si les listes sont vides.
        """
        if not y_true or not y_pred:
            raise ValueError(
                "Les listes de prédictions sont vides. "
                "Fournir au moins un exemple pour l'évaluation."
            )

        if len(y_true) != len(y_pred):
            raise ValueError(
                f"Tailles différentes : y_true={len(y_true)}, y_pred={len(y_pred)}"
            )

        # Vérifier les labels inconnus
        known_set = set(self.labels)
        unknown_true = set(y_true) - known_set
        unknown_pred = set(y_pred) - known_set
        if unknown_true:
            logger.warning(
                "Labels inconnus dans y_true : %s", unknown_true
            )
        if unknown_pred:
            logger.warning(
                "Labels inconnus dans y_pred : %s", unknown_pred
            )

        # Calcul des métriques
        if _HAS_SKLEARN:
            accuracy = float(accuracy_score(y_true, y_pred))
            f1_macro = float(f1_score(
                y_true, y_pred, labels=self.labels,
                average="macro", zero_division=0,
            ))
            f1_per_class_values = f1_score(
                y_true, y_pred, labels=self.labels,
                average=None, zero_division=0,
            )
            f1_per_class = {
                label: round(float(val), 6)
                for label, val in zip(self.labels, f1_per_class_values)
            }
            prec_macro = float(precision_score(
                y_true, y_pred, labels=self.labels,
                average="macro", zero_division=0,
            ))
            rec_macro = float(recall_score(
                y_true, y_pred, labels=self.labels,
                average="macro", zero_division=0,
            ))
            cm = sk_confusion_matrix(
                y_true, y_pred, labels=self.labels,
            ).tolist()
        else:
            accuracy = _manual_accuracy(y_true, y_pred)
            f1_per_class = _manual_f1_per_class(y_true, y_pred, self.labels)
            f1_values = list(f1_per_class.values())
            f1_macro = sum(f1_values) / len(f1_values) if f1_values else 0.0
            prec_macro = _manual_precision_macro(y_true, y_pred, self.labels)
            rec_macro = _manual_recall_macro(y_true, y_pred, self.labels)
            cm = _manual_confusion_matrix(y_true, y_pred, self.labels)

        timestamp = datetime.now(timezone.utc).isoformat()

        report = EvaluationReport(
            accuracy=round(accuracy, 6),
            f1_macro=round(f1_macro, 6),
            f1_per_class=f1_per_class,
            precision_macro=round(prec_macro, 6),
            recall_macro=round(rec_macro, 6),
            confusion_matrix=cm,
            labels=list(self.labels),
            n_samples=len(y_true),
            timestamp=timestamp,
        )

        logger.info(
            "Évaluation terminée : %d exemples, F1 macro=%.4f, Accuracy=%.4f",
            report.n_samples, report.f1_macro, report.accuracy,
        )
        return report

    def evaluate_from_dataset(
        self, classifier, dataset: list[dict]
    ) -> EvaluationReport:
        """Évalue un classifieur sur un dataset annoté.

        Args:
            classifier: Instance avec méthode predict_batch(texts) → list[dict].
            dataset: Liste de dicts avec clés 'text' et 'sentiment_label'.

        Returns:
            EvaluationReport avec toutes les métriques.

        Raises:
            ValueError: Si le dataset est vide.
        """
        if not dataset:
            raise ValueError(
                "Le dataset est vide. Fournir au moins un exemple."
            )

        texts = [item["text"] for item in dataset]
        y_true = [item["sentiment_label"] for item in dataset]

        logger.info("Évaluation sur %d exemples...", len(texts))
        predictions = classifier.predict_batch(texts)
        y_pred = [pred["label"] for pred in predictions]

        return self.evaluate(y_true, y_pred)


# ---------------------------------------------------------------------------
# Comparaison de rapports
# ---------------------------------------------------------------------------

def compare_reports(
    report_a: EvaluationReport, report_b: EvaluationReport
) -> dict:
    """Compare deux rapports d'évaluation (avant/après fine-tuning).

    Args:
        report_a: Rapport de référence (avant).
        report_b: Rapport à comparer (après).

    Returns:
        Dict avec les deltas pour chaque métrique principale.
    """
    result = {
        "f1_macro_delta": round(report_b.f1_macro - report_a.f1_macro, 6),
        "accuracy_delta": round(report_b.accuracy - report_a.accuracy, 6),
        "precision_macro_delta": round(
            report_b.precision_macro - report_a.precision_macro, 6
        ),
        "recall_macro_delta": round(
            report_b.recall_macro - report_a.recall_macro, 6
        ),
        "n_samples_a": report_a.n_samples,
        "n_samples_b": report_b.n_samples,
        "f1_per_class_delta": {},
    }

    # Delta F1 par classe
    all_labels = set(report_a.f1_per_class.keys()) | set(
        report_b.f1_per_class.keys()
    )
    for label in sorted(all_labels):
        f1_a = report_a.f1_per_class.get(label, 0.0)
        f1_b = report_b.f1_per_class.get(label, 0.0)
        result["f1_per_class_delta"][label] = round(f1_b - f1_a, 6)

    # Résumé
    improved = result["f1_macro_delta"] > 0
    result["improved"] = improved
    result["summary"] = (
        f"F1 macro : {report_a.f1_macro:.4f} → {report_b.f1_macro:.4f} "
        f"({'↑' if improved else '↓'} {abs(result['f1_macro_delta']):.4f})"
    )

    logger.info("Comparaison : %s", result["summary"])
    return result
