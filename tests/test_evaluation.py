"""Tests TDD pour core/analysis/evaluation.py.

Teste : évaluation de prédictions, métriques (F1, accuracy, confusion matrix),
critères Phase 0, sérialisation JSON, rapport markdown, comparaison.
Le classifieur est mocké — aucun modèle requis.
"""

import json
import logging
import os
import sys
from dataclasses import asdict
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import SENTIMENT_LABELS  # noqa: E402
from core.analysis.evaluation import (  # noqa: E402
    ClassifierEvaluator,
    EvaluationReport,
    compare_reports,
)

LABELS = SENTIMENT_LABELS  # ["très_positif", "positif", "neutre", "négatif", "très_négatif"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_perfect_predictions(n_per_class: int = 20) -> tuple[list[str], list[str]]:
    """Génère des prédictions parfaites pour chaque classe."""
    y_true = []
    y_pred = []
    for label in LABELS:
        y_true.extend([label] * n_per_class)
        y_pred.extend([label] * n_per_class)
    return y_true, y_pred


def _make_good_predictions(n_per_class: int = 20) -> tuple[list[str], list[str]]:
    """Génère des prédictions majoritairement correctes (F1 ~ 0.75-0.85)."""
    y_true = []
    y_pred = []
    for i, label in enumerate(LABELS):
        correct = int(n_per_class * 0.8)  # 80% correct
        wrong = n_per_class - correct
        y_true.extend([label] * n_per_class)
        y_pred.extend([label] * correct)
        # Les erreurs vont vers la classe voisine
        neighbor = LABELS[(i + 1) % len(LABELS)]
        y_pred.extend([neighbor] * wrong)
    return y_true, y_pred


def _make_bad_predictions(n_per_class: int = 20) -> tuple[list[str], list[str]]:
    """Génère des prédictions aléatoires/mauvaises (F1 < 0.50)."""
    y_true = []
    y_pred = []
    for i, label in enumerate(LABELS):
        y_true.extend([label] * n_per_class)
        # Tout classer comme neutre
        y_pred.extend(["neutre"] * n_per_class)
    return y_true, y_pred


def _make_report(f1_macro: float, accuracy: float,
                 f1_per_class: dict | None = None) -> EvaluationReport:
    """Crée un rapport avec des valeurs contrôlées pour les tests de critères."""
    if f1_per_class is None:
        f1_per_class = {label: f1_macro for label in LABELS}
    return EvaluationReport(
        accuracy=accuracy,
        f1_macro=f1_macro,
        f1_per_class=f1_per_class,
        precision_macro=f1_macro,
        recall_macro=f1_macro,
        confusion_matrix=[[0] * len(LABELS) for _ in LABELS],
        labels=list(LABELS),
        n_samples=100,
        timestamp="2026-03-28T00:00:00",
    )


# ---------------------------------------------------------------------------
# Tests évaluation de base
# ---------------------------------------------------------------------------

def test_evaluate_predictions_parfaites() -> None:
    """Prédictions parfaites → F1 = 1.0, accuracy = 1.0."""
    evaluator = ClassifierEvaluator(labels=LABELS)
    y_true, y_pred = _make_perfect_predictions()
    report = evaluator.evaluate(y_true, y_pred)
    assert report.f1_macro == pytest.approx(1.0, abs=0.001)
    assert report.accuracy == pytest.approx(1.0, abs=0.001)


def test_evaluate_predictions_aleatoires() -> None:
    """Prédictions aléatoires → F1 < 1.0."""
    evaluator = ClassifierEvaluator(labels=LABELS)
    y_true, y_pred = _make_bad_predictions()
    report = evaluator.evaluate(y_true, y_pred)
    assert report.f1_macro < 1.0


def test_f1_par_classe() -> None:
    """Chaque classe a un F1 dans le rapport."""
    evaluator = ClassifierEvaluator(labels=LABELS)
    y_true, y_pred = _make_good_predictions()
    report = evaluator.evaluate(y_true, y_pred)
    for label in LABELS:
        assert label in report.f1_per_class
        assert 0.0 <= report.f1_per_class[label] <= 1.0


def test_confusion_matrix_dimensions() -> None:
    """La matrice de confusion doit être 5×5."""
    evaluator = ClassifierEvaluator(labels=LABELS)
    y_true, y_pred = _make_good_predictions()
    report = evaluator.evaluate(y_true, y_pred)
    assert len(report.confusion_matrix) == 5
    for row in report.confusion_matrix:
        assert len(row) == 5


# ---------------------------------------------------------------------------
# Tests critères Phase 0
# ---------------------------------------------------------------------------

def test_meets_phase0_criteria_ok() -> None:
    """F1 macro ≥ 0.70, par classe ≥ 0.60, accuracy ≥ 0.65 → True."""
    report = _make_report(
        f1_macro=0.75,
        accuracy=0.70,
        f1_per_class={label: 0.65 for label in LABELS},
    )
    assert report.meets_phase0_criteria() is True


def test_meets_phase0_criteria_fail_f1_macro() -> None:
    """F1 macro < 0.70 → False."""
    report = _make_report(f1_macro=0.55, accuracy=0.70)
    assert report.meets_phase0_criteria() is False


def test_meets_phase0_criteria_fail_f1_per_class() -> None:
    """F1 d'une classe < 0.60 → False."""
    f1_per_class = {label: 0.75 for label in LABELS}
    f1_per_class["négatif"] = 0.50  # une classe trop basse
    report = _make_report(
        f1_macro=0.72,
        accuracy=0.70,
        f1_per_class=f1_per_class,
    )
    assert report.meets_phase0_criteria() is False


def test_meets_phase0_criteria_fail_accuracy() -> None:
    """Accuracy < 0.65 → False."""
    report = _make_report(f1_macro=0.75, accuracy=0.60)
    assert report.meets_phase0_criteria() is False


# ---------------------------------------------------------------------------
# Tests sérialisation
# ---------------------------------------------------------------------------

def test_report_serialization_json(tmp_path: Path) -> None:
    """save() + load() round-trip doit préserver toutes les valeurs."""
    report = _make_report(f1_macro=0.72, accuracy=0.68)
    path = str(tmp_path / "report.json")
    report.save(path)
    loaded = EvaluationReport.load(path)
    assert loaded.f1_macro == pytest.approx(report.f1_macro, abs=0.001)
    assert loaded.accuracy == pytest.approx(report.accuracy, abs=0.001)
    assert loaded.n_samples == report.n_samples
    assert loaded.labels == report.labels
    assert loaded.f1_per_class == report.f1_per_class


def test_report_to_dict() -> None:
    """to_dict() doit retourner un dict JSON-sérialisable."""
    report = _make_report(f1_macro=0.72, accuracy=0.68)
    d = report.to_dict()
    assert isinstance(d, dict)
    # Vérifier que c'est JSON-sérialisable
    json.dumps(d, ensure_ascii=False)
    assert d["f1_macro"] == pytest.approx(0.72, abs=0.001)


# ---------------------------------------------------------------------------
# Tests rapport markdown
# ---------------------------------------------------------------------------

def test_report_to_markdown() -> None:
    """Le rapport markdown doit contenir les tableaux attendus."""
    report = _make_report(f1_macro=0.72, accuracy=0.68)
    md = report.to_markdown()
    assert "F1 macro" in md or "f1_macro" in md.lower()
    assert "Accuracy" in md or "accuracy" in md.lower()
    assert "0.72" in md or "72" in md
    assert "Phase 0" in md or "phase" in md.lower()
    # Doit contenir une matrice
    assert "|" in md


# ---------------------------------------------------------------------------
# Tests compare_reports
# ---------------------------------------------------------------------------

def test_compare_reports() -> None:
    """Deltas calculés correctement entre deux rapports."""
    report_a = _make_report(f1_macro=0.55, accuracy=0.50)
    report_b = _make_report(f1_macro=0.72, accuracy=0.68)
    deltas = compare_reports(report_a, report_b)
    assert "f1_macro_delta" in deltas
    assert deltas["f1_macro_delta"] == pytest.approx(0.17, abs=0.01)
    assert "accuracy_delta" in deltas
    assert deltas["accuracy_delta"] == pytest.approx(0.18, abs=0.01)


# ---------------------------------------------------------------------------
# Tests evaluate_from_dataset
# ---------------------------------------------------------------------------

def test_evaluate_from_dataset() -> None:
    """Évaluation depuis un dataset avec classifieur mocké."""
    evaluator = ClassifierEvaluator(labels=LABELS)
    mock_classifier = MagicMock()
    mock_classifier.predict_batch.return_value = [
        {"label": "positif", "confidence": 0.9, "logits": [0.0] * 5},
        {"label": "négatif", "confidence": 0.8, "logits": [0.0] * 5},
        {"label": "neutre", "confidence": 0.7, "logits": [0.0] * 5},
    ]
    dataset = [
        {"text": "Ramy c'est bon", "sentiment_label": "positif"},
        {"text": "Le goût est mauvais", "sentiment_label": "négatif"},
        {"text": "C'est normal", "sentiment_label": "neutre"},
    ]
    report = evaluator.evaluate_from_dataset(mock_classifier, dataset)
    assert report.n_samples == 3
    assert report.accuracy == pytest.approx(1.0, abs=0.001)


# ---------------------------------------------------------------------------
# Tests cas limites
# ---------------------------------------------------------------------------

def test_empty_dataset_raises() -> None:
    """Dataset vide → erreur propre."""
    evaluator = ClassifierEvaluator(labels=LABELS)
    with pytest.raises(ValueError, match="[Vv]ide|[Ee]mpty|aucun"):
        evaluator.evaluate([], [])


def test_labels_mismatch_warning(caplog) -> None:
    """Label inconnu dans y_pred → warning loggé."""
    evaluator = ClassifierEvaluator(labels=LABELS)
    y_true = ["positif", "négatif"]
    y_pred = ["positif", "label_inconnu"]
    with caplog.at_level(logging.WARNING):
        report = evaluator.evaluate(y_true, y_pred)
    assert any("inconnu" in record.message.lower() or "unknown" in record.message.lower()
               for record in caplog.records)
