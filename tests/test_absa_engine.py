"""Tests unitaires pour le moteur ABSA RamyPulse."""

from pathlib import Path

import pandas as pd

from config import SENTIMENT_LABELS
from core.analysis import absa_engine


def build_input_dataframe(rows: list[dict]) -> pd.DataFrame:
    """Construit un DataFrame d'entrée minimal pour les tests ABSA."""
    return pd.DataFrame(rows, columns=["text", "channel", "source_url", "timestamp"])


def fake_classifier(text: str) -> dict[str, object]:
    """Retourne un sentiment déterministe en fonction du texte fourni."""
    lowered = text.lower()
    if "ghali" in lowered or "cher" in lowered:
        return {"label": "négatif", "confidence": 0.87, "logits": [0.1, 0.2, 0.1, 0.5, 0.1]}
    if "bon" in lowered or "goût" in lowered or "frais" in lowered:
        return {"label": "positif", "confidence": 0.93, "logits": [0.1, 0.6, 0.1, 0.1, 0.1]}
    return {"label": "neutre", "confidence": 0.51, "logits": [0.2, 0.2, 0.2, 0.2, 0.2]}


def test_output_dataframe_contains_required_columns(monkeypatch) -> None:
    """Vérifie que le DataFrame de sortie contient toutes les colonnes attendues."""
    df = build_input_dataframe(
        [
            {
                "text": "le goût est bon.",
                "channel": "facebook",
                "source_url": "https://x/1",
                "timestamp": "2026-01-01",
            }
        ]
    )

    monkeypatch.setattr(absa_engine, "classify_sentiment", fake_classifier)
    monkeypatch.setattr(
        absa_engine,
        "extract_aspects",
        lambda text: [{"aspect": "goût", "mention": "goût", "start": 3, "end": 7}],
    )

    result = absa_engine.run_absa_pipeline(df)

    assert list(result.columns) == [
        "text",
        "channel",
        "source_url",
        "timestamp",
        "sentiment_label",
        "confidence",
        "aspects",
        "aspect_sentiments",
    ]


def test_text_with_one_aspect_produces_one_aspect_sentiment(monkeypatch) -> None:
    """Vérifie qu'un texte avec un aspect produit une seule annotation d'aspect."""
    df = build_input_dataframe(
        [
            {
                "text": "Le goût est bon.",
                "channel": "facebook",
                "source_url": "https://x/1",
                "timestamp": "2026-01-01",
            }
        ]
    )

    monkeypatch.setattr(absa_engine, "classify_sentiment", fake_classifier)
    monkeypatch.setattr(
        absa_engine,
        "extract_aspects",
        lambda text: [{"aspect": "goût", "mention": "goût", "start": 3, "end": 7}],
    )

    result = absa_engine.run_absa_pipeline(df)
    annotations = result.loc[0, "aspect_sentiments"]

    assert result.loc[0, "sentiment_label"] == "positif"
    assert result.loc[0, "aspects"] == ["goût"]
    assert len(annotations) == 1
    assert annotations[0] == {
        "aspect": "goût",
        "mention": "goût",
        "sentiment": "positif",
        "confidence": 0.93,
    }


def test_text_with_three_aspects_produces_three_aspect_sentiments(monkeypatch) -> None:
    """Vérifie qu'un texte multi-aspects produit une annotation par mention détectée."""
    df = build_input_dataframe(
        [
            {
                "text": "Le goût est bon. Le prix est ghali. L'emballage est correct.",
                "channel": "youtube",
                "source_url": "https://x/2",
                "timestamp": "2026-01-02",
            }
        ]
    )

    monkeypatch.setattr(absa_engine, "classify_sentiment", fake_classifier)
    monkeypatch.setattr(
        absa_engine,
        "extract_aspects",
        lambda text: [
            {"aspect": "goût", "mention": "goût", "start": 3, "end": 7},
            {"aspect": "prix", "mention": "prix", "start": 20, "end": 24},
            {"aspect": "emballage", "mention": "emballage", "start": 38, "end": 48},
        ],
    )

    result = absa_engine.run_absa_pipeline(df)
    annotations = result.loc[0, "aspect_sentiments"]

    assert result.loc[0, "aspects"] == ["goût", "prix", "emballage"]
    assert len(annotations) == 3
    assert [item["aspect"] for item in annotations] == ["goût", "prix", "emballage"]


def test_text_without_aspect_keeps_global_sentiment_and_empty_annotations(monkeypatch) -> None:
    """Vérifie qu'un texte sans aspect conserve le sentiment global et aucune annotation d'aspect."""
    df = build_input_dataframe(
        [
            {
                "text": "Avis global sans détail.",
                "channel": "facebook",
                "source_url": "https://x/3",
                "timestamp": "2026-01-03",
            }
        ]
    )

    monkeypatch.setattr(absa_engine, "classify_sentiment", fake_classifier)
    monkeypatch.setattr(absa_engine, "extract_aspects", lambda text: [])

    result = absa_engine.run_absa_pipeline(df)

    assert result.loc[0, "sentiment_label"] == "neutre"
    assert result.loc[0, "confidence"] == 0.51
    assert result.loc[0, "aspects"] == []
    assert result.loc[0, "aspect_sentiments"] == []


def test_pipeline_saves_output_parquet(monkeypatch, tmp_path: Path) -> None:
    """Vérifie que le pipeline sauvegarde le parquet annoté sur disque."""
    df = build_input_dataframe(
        [
            {
                "text": "Le goût est bon.",
                "channel": "facebook",
                "source_url": "https://x/4",
                "timestamp": "2026-01-04",
            }
        ]
    )
    output_path = tmp_path / "annotated.parquet"

    monkeypatch.setattr(absa_engine, "classify_sentiment", fake_classifier)
    monkeypatch.setattr(
        absa_engine,
        "extract_aspects",
        lambda text: [{"aspect": "goût", "mention": "goût", "start": 3, "end": 7}],
    )

    absa_engine.run_absa_pipeline(df, output_path=output_path)

    assert output_path.exists()
    reloaded = pd.read_parquet(output_path)
    assert list(reloaded.columns) == [
        "text",
        "channel",
        "source_url",
        "timestamp",
        "sentiment_label",
        "confidence",
        "aspects",
        "aspect_sentiments",
    ]
    assert len(reloaded) == 1


def test_pipeline_peut_desactiver_persistance(monkeypatch, tmp_path: Path) -> None:
    """Le pipeline ABSA doit pouvoir calculer sans ecrire de parquet."""
    df = build_input_dataframe(
        [
            {
                "text": "Le goût est bon.",
                "channel": "facebook",
                "source_url": "https://x/4",
                "timestamp": "2026-01-04",
            }
        ]
    )
    output_path = tmp_path / "annotated.parquet"

    monkeypatch.setattr(absa_engine, "classify_sentiment", fake_classifier)
    monkeypatch.setattr(
        absa_engine,
        "extract_aspects",
        lambda text: [{"aspect": "goût", "mention": "goût", "start": 3, "end": 7}],
    )

    result = absa_engine.run_absa_pipeline(df, output_path=output_path, persist_output=False)

    assert len(result) == 1
    assert not output_path.exists()


def test_extract_sentence_handles_arabic_punctuation() -> None:
    """La fonction d'extraction de phrase doit gérer la ponctuation arabe (؟ ، ؛)."""
    text = "المنتج جيد؟ الطعم ممتاز، السعر مقبول"
    # L'aspect "الطعم" (goût) commence à l'index 13, finit à 18
    sentence = absa_engine._extract_sentence_for_span(text, 13, 18)
    # La phrase doit être séparée par le ؟ arabe
    assert "المنتج جيد" not in sentence
    assert "الطعم" in sentence


def test_extract_sentence_arabic_question_mark() -> None:
    """Le point d'interrogation arabe ؟ doit servir de séparateur de phrases."""
    text = "هل هذا غالي؟ الجودة ممتازة"
    sentence = absa_engine._extract_sentence_for_span(text, 14, 20)
    assert "غالي" not in sentence
    assert "الجودة" in sentence


def test_aspect_sentiments_utilisent_labels_prd(monkeypatch) -> None:
    """PRD: les sentiments par aspect doivent utiliser les 5 classes discrètes officielles."""
    df = build_input_dataframe(
        [
            {
                "text": "Le goût est bon mais le prix est ghali.",
                "channel": "facebook",
                "source_url": "https://x/5",
                "timestamp": "2026-01-05",
            }
        ]
    )

    monkeypatch.setattr(absa_engine, "classify_sentiment", fake_classifier)
    monkeypatch.setattr(
        absa_engine,
        "extract_aspects",
        lambda text: [
            {"aspect": "goût", "mention": "goût", "start": 3, "end": 7},
            {"aspect": "prix", "mention": "prix", "start": 25, "end": 29},
        ],
    )

    result = absa_engine.run_absa_pipeline(df)
    for annotation in result.loc[0, "aspect_sentiments"]:
        assert annotation["sentiment"] in SENTIMENT_LABELS, (
            f"Label aspect invalide: '{annotation['sentiment']}'. "
            f"Attendu un de: {SENTIMENT_LABELS}"
        )
        assert 0.0 <= annotation["confidence"] <= 1.0
        assert "aspect" in annotation
        assert "mention" in annotation


def test_pipeline_handles_hundred_texts_without_crashing(monkeypatch) -> None:
    """Vérifie que le pipeline traite 100 lignes sans erreur."""
    df = build_input_dataframe(
        [
            {
                "text": f"Le goût est bon numéro {index}.",
                "channel": "facebook",
                "source_url": f"https://x/{index}",
                "timestamp": "2026-01-05",
            }
            for index in range(100)
        ]
    )

    monkeypatch.setattr(absa_engine, "classify_sentiment", fake_classifier)
    monkeypatch.setattr(
        absa_engine,
        "extract_aspects",
        lambda text: [{"aspect": "goût", "mention": "goût", "start": 3, "end": 7}],
    )

    result = absa_engine.run_absa_pipeline(df)

    assert len(result) == 100
    assert all(len(item) == 1 for item in result["aspect_sentiments"])
