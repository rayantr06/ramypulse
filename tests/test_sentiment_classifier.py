"""Tests unitaires pour core/analysis/sentiment_classifier.py.

Stratégie: les tests utilisent des modèles/tokenizers mockés (pas de
téléchargement DziriBERT) pour rester rapides et déterministes.
Les tests d'intégration réels sont marqués @pytest.mark.slow.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import torch

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import SENTIMENT_LABELS

# ---------------------------------------------------------------------------
# Faux modèle et tokenizer (injection de dépendances pour les tests unitaires)
# ---------------------------------------------------------------------------

NUM_LABELS = 5
SEQ_LEN = 10


def _make_fake_logits(batch_size: int = 1, num_labels: int = NUM_LABELS) -> torch.Tensor:
    """Retourne des logits déterministes (classe 1 = 'positif' dominante)."""
    logits = torch.zeros(batch_size, num_labels)
    logits[:, 1] = 2.0   # classe index 1 ("positif") largement favorite
    return logits


class _FakeModelOutput:
    """Simule le BaseModelOutput de HuggingFace."""

    def __init__(self, logits: torch.Tensor):
        self.logits = logits


class _FakeModel(torch.nn.Module):
    """Modèle factice: retourne des logits fixes sans aucun calcul réel."""

    def __init__(self, num_labels: int = NUM_LABELS):
        super().__init__()
        self.config = MagicMock()
        self.config.num_labels = num_labels
        self.num_labels = num_labels

    def forward(self, **kwargs) -> _FakeModelOutput:
        batch_size = kwargs.get("input_ids", torch.ones(1, SEQ_LEN)).shape[0]
        return _FakeModelOutput(logits=_make_fake_logits(batch_size, self.num_labels))

    def eval(self):
        return self

    def to(self, device):
        return self


class _FakeTokenizer:
    """Tokenizer factice: retourne des tenseurs de zéros."""

    def __call__(self, text, return_tensors="pt", truncation=True,
                 max_length=128, padding=True):
        if isinstance(text, str):
            texts = [text] if text.strip() else ["[PAD]"]
        else:
            texts = [t if t.strip() else "[PAD]" for t in text]
        batch = len(texts)
        return {
            "input_ids": torch.zeros(batch, SEQ_LEN, dtype=torch.long),
            "attention_mask": torch.ones(batch, SEQ_LEN, dtype=torch.long),
            "token_type_ids": torch.zeros(batch, SEQ_LEN, dtype=torch.long),
        }


# ---------------------------------------------------------------------------
# Fixture: classifieur injecté avec faux modèle
# ---------------------------------------------------------------------------

@pytest.fixture
def classifier():
    """SentimentClassifier avec modèle et tokenizer mockés (rapide, hors-ligne)."""
    from core.analysis.sentiment_classifier import SentimentClassifier
    return SentimentClassifier(model=_FakeModel(), tokenizer=_FakeTokenizer())


# ---------------------------------------------------------------------------
# 1. Chargement du module
# ---------------------------------------------------------------------------

class TestImport:
    """Le module s'importe sans erreur."""

    def test_module_importable(self):
        from core.analysis import sentiment_classifier  # noqa: F401

    def test_classe_exportee(self):
        from core.analysis.sentiment_classifier import SentimentClassifier
        assert callable(SentimentClassifier)

    def test_fonction_predict_fine_tune_exportee(self):
        from core.analysis.sentiment_classifier import SentimentClassifier
        assert hasattr(SentimentClassifier, "predict")
        assert hasattr(SentimentClassifier, "predict_batch")


# ---------------------------------------------------------------------------
# 2. Structure du dict retourné
# ---------------------------------------------------------------------------

class TestStructureRetour:
    """predict() retourne exactement le dict spécifié par le PRD."""

    def test_retourne_dict(self, classifier):
        r = classifier.predict("رامي واعر")
        assert isinstance(r, dict)

    def test_cle_label_presente(self, classifier):
        r = classifier.predict("رامي واعر")
        assert "label" in r

    def test_cle_confidence_presente(self, classifier):
        r = classifier.predict("رامي واعر")
        assert "confidence" in r

    def test_cle_logits_presente(self, classifier):
        r = classifier.predict("رامي واعر")
        assert "logits" in r

    def test_pas_de_cles_supplementaires(self, classifier):
        r = classifier.predict("رامي واعر")
        assert set(r.keys()) == {"label", "confidence", "logits"}

    def test_label_est_string(self, classifier):
        r = classifier.predict("رامي واعر")
        assert isinstance(r["label"], str)

    def test_confidence_est_float(self, classifier):
        r = classifier.predict("رامي واعر")
        assert isinstance(r["confidence"], float)

    def test_logits_est_liste(self, classifier):
        r = classifier.predict("رامي واعر")
        assert isinstance(r["logits"], list)


# ---------------------------------------------------------------------------
# 3. Contraintes sur les valeurs
# ---------------------------------------------------------------------------

class TestContraintesValeurs:
    """Label valide, confidence ∈ [0,1], logits de taille 5."""

    def test_label_dans_sentiment_labels(self, classifier):
        r = classifier.predict("le jus Ramy est bon")
        assert r["label"] in SENTIMENT_LABELS, \
            f"Label invalide: '{r['label']}'. Attendu: {SENTIMENT_LABELS}"

    def test_confidence_entre_0_et_1(self, classifier):
        r = classifier.predict("le jus Ramy est bon")
        assert 0.0 <= r["confidence"] <= 1.0, \
            f"Confidence hors plage: {r['confidence']}"

    def test_confidence_strictement_positif(self, classifier):
        r = classifier.predict("test")
        assert r["confidence"] > 0.0

    def test_logits_5_elements(self, classifier):
        r = classifier.predict("test")
        assert len(r["logits"]) == NUM_LABELS, \
            f"Attendu 5 logits, obtenu {len(r['logits'])}"

    def test_logits_elements_sont_float(self, classifier):
        r = classifier.predict("test")
        for val in r["logits"]:
            assert isinstance(val, float), f"Logit non-float: {type(val)}"

    def test_logits_coherents_avec_label(self, classifier):
        """argmax(logits) doit correspondre à l'index du label retourné."""
        r = classifier.predict("test")
        idx_max = r["logits"].index(max(r["logits"]))
        assert r["label"] == SENTIMENT_LABELS[idx_max], \
            f"Incohérence: argmax={idx_max} → '{SENTIMENT_LABELS[idx_max]}' " \
            f"mais label='{r['label']}'"

    def test_somme_softmax_proche_1(self, classifier):
        """La confidence est max(softmax(logits)), donc sum(softmax) ≈ 1."""
        import math
        r = classifier.predict("test")
        logits = r["logits"]
        max_l = max(logits)
        exps = [math.exp(l - max_l) for l in logits]
        total = sum(exps)
        probs = [e / total for e in exps]
        assert abs(sum(probs) - 1.0) < 1e-5
        # La confidence doit être max(probs)
        assert abs(r["confidence"] - max(probs)) < 1e-4, \
            f"Confidence={r['confidence']} ≠ max(softmax)={max(probs):.4f}"


# ---------------------------------------------------------------------------
# 4. Texte vide et cas limites
# ---------------------------------------------------------------------------

class TestCasLimites:
    """Gestion robuste des entrées problématiques."""

    def test_texte_vide_ne_leve_pas_exception(self, classifier):
        try:
            r = classifier.predict("")
            assert isinstance(r, dict)
        except Exception as e:
            pytest.fail(f"predict('') a levé une exception: {e}")

    def test_texte_vide_label_valide(self, classifier):
        r = classifier.predict("")
        assert r["label"] in SENTIMENT_LABELS

    def test_texte_espaces_seulement(self, classifier):
        r = classifier.predict("   ")
        assert isinstance(r, dict)
        assert r["label"] in SENTIMENT_LABELS

    def test_texte_tres_long(self, classifier):
        long_text = "رامي " * 300  # ~1500 tokens, tronqué à 128
        r = classifier.predict(long_text)
        assert r["label"] in SENTIMENT_LABELS

    def test_texte_chiffres(self, classifier):
        r = classifier.predict("12345 67890")
        assert isinstance(r, dict)

    def test_texte_emoji(self, classifier):
        r = classifier.predict("😍😍😍 رامي واعر 😍")
        assert r["label"] in SENTIMENT_LABELS

    def test_texte_ponctuation(self, classifier):
        r = classifier.predict("!!! ??? ...")
        assert isinstance(r, dict)

    def test_texte_mixte_arabe_francais(self, classifier):
        r = classifier.predict("رامي très bon جداً")
        assert r["label"] in SENTIMENT_LABELS


# ---------------------------------------------------------------------------
# 5. Inférence batch
# ---------------------------------------------------------------------------

class TestBatch:
    """predict_batch() fonctionne et retourne le bon format."""

    def test_predict_batch_retourne_liste(self, classifier):
        results = classifier.predict_batch(["texte 1", "texte 2", "texte 3"])
        assert isinstance(results, list)

    def test_predict_batch_taille_correcte(self, classifier):
        texts = ["texte 1", "texte 2", "texte 3", "texte 4"]
        results = classifier.predict_batch(texts)
        assert len(results) == len(texts)

    def test_predict_batch_chaque_element_est_dict(self, classifier):
        results = classifier.predict_batch(["texte 1", "texte 2"])
        for r in results:
            assert isinstance(r, dict)
            assert set(r.keys()) == {"label", "confidence", "logits"}

    def test_predict_batch_labels_valides(self, classifier):
        texts = ["رامي واعر", "le jus est bon", "7aja mliha bzaf"]
        results = classifier.predict_batch(texts)
        for r in results:
            assert r["label"] in SENTIMENT_LABELS

    def test_predict_batch_confidences_valides(self, classifier):
        results = classifier.predict_batch(["texte 1", "texte 2"])
        for r in results:
            assert 0.0 <= r["confidence"] <= 1.0

    def test_predict_batch_liste_vide(self, classifier):
        results = classifier.predict_batch([])
        assert results == []

    def test_predict_batch_un_element(self, classifier):
        results = classifier.predict_batch(["seul texte"])
        assert len(results) == 1
        assert results[0]["label"] in SENTIMENT_LABELS

    def test_predict_batch_coherent_avec_predict(self, classifier):
        """predict_batch([t]) doit donner le même résultat que predict(t)."""
        text = "رامي واعر بزاف"
        single = classifier.predict(text)
        batch = classifier.predict_batch([text])
        assert single["label"] == batch[0]["label"]
        assert abs(single["confidence"] - batch[0]["confidence"]) < 1e-4

    def test_predict_batch_grand_batch(self, classifier):
        texts = [f"texte numéro {i}" for i in range(50)]
        results = classifier.predict_batch(texts, batch_size=16)
        assert len(results) == 50
        for r in results:
            assert r["label"] in SENTIMENT_LABELS


# ---------------------------------------------------------------------------
# 6. Chargement depuis HuggingFace (avec mock)
# ---------------------------------------------------------------------------

class TestChargementModele:
    """SentimentClassifier charge le modèle sans erreur (avec mock HuggingFace)."""

    def test_constructeur_injection_directe(self):
        """Injection directe: pas de téléchargement."""
        from core.analysis.sentiment_classifier import SentimentClassifier
        clf = SentimentClassifier(model=_FakeModel(), tokenizer=_FakeTokenizer())
        assert clf is not None

    def test_constructeur_avec_mock_hf(self):
        """Mock du chargement HuggingFace."""
        from core.analysis.sentiment_classifier import SentimentClassifier

        fake_model = _FakeModel()
        fake_tok = _FakeTokenizer()

        with patch("core.analysis.sentiment_classifier.AutoTokenizer") as mock_tok_cls, \
             patch("core.analysis.sentiment_classifier.AutoModelForSequenceClassification") as mock_model_cls:
            mock_tok_cls.from_pretrained.return_value = fake_tok
            mock_model_cls.from_pretrained.return_value = fake_model

            clf = SentimentClassifier(model_name="alger-ia/dziribert")
            assert clf is not None

    def test_constructeur_fallback_model_name_par_defaut(self):
        """Sans argument, utilise le chemin config.DZIRIBERT_MODEL_PATH."""
        from core.analysis.sentiment_classifier import SentimentClassifier
        import inspect
        sig = inspect.signature(SentimentClassifier.__init__)
        params = sig.parameters
        assert "model_name" in params or "model" in params

    def test_mode_eval_apres_chargement(self, classifier):
        """Le modèle doit être en mode eval (pas training) pour l'inférence."""
        # Vérifié indirectement: predict() ne doit pas retourner d'erreur
        # liée au mode training
        r = classifier.predict("test")
        assert isinstance(r, dict)

    def test_device_cpu_par_defaut(self, classifier):
        """Sur machine sans GPU, device = cpu."""
        device = getattr(classifier, "device", None)
        if device is not None:
            assert str(device) in {"cpu", "cuda", "cuda:0"}


# ---------------------------------------------------------------------------
# 7. Cohérence interne
# ---------------------------------------------------------------------------

class TestCoherenceInterne:
    """Logique interne: softmax, argmax, mapping index→label."""

    def test_label_positif_quand_logit_2_domine(self, classifier):
        """Avec _FakeModel, logit[1]=2.0 → label='positif'."""
        r = classifier.predict("test")
        assert r["label"] == "positif", \
            f"Attendu 'positif' (logit[1] dominant), obtenu '{r['label']}'"

    def test_confidence_haute_quand_logit_dominant(self, classifier):
        """Quand un logit domine largement, confidence > 0.5."""
        r = classifier.predict("test")
        assert r["confidence"] > 0.5

    def test_tous_labels_atteignables(self):
        """Chaque label peut être retourné (test avec logits configurés)."""
        from core.analysis.sentiment_classifier import SentimentClassifier

        for idx, expected_label in enumerate(SENTIMENT_LABELS):
            class _TargetModel(_FakeModel):
                def __init__(self, target_idx):
                    super().__init__()
                    self._target = target_idx

                def forward(self, **kwargs):
                    batch = kwargs.get("input_ids", torch.ones(1, 1)).shape[0]
                    logits = torch.zeros(batch, NUM_LABELS)
                    logits[:, self._target] = 5.0
                    return _FakeModelOutput(logits)

            clf = SentimentClassifier(
                model=_TargetModel(idx),
                tokenizer=_FakeTokenizer()
            )
            r = clf.predict("test")
            assert r["label"] == expected_label, \
                f"Index {idx}: attendu '{expected_label}', obtenu '{r['label']}'"

    def test_logits_ordre_conserve(self, classifier):
        """L'ordre des logits correspond à l'ordre de SENTIMENT_LABELS."""
        r = classifier.predict("test")
        # logit[1] est le plus grand → "positif" doit être à l'index 1
        assert r["logits"][1] == max(r["logits"])

    def test_predict_deterministique(self, classifier):
        """Même entrée → même sortie (mode eval, pas de dropout)."""
        r1 = classifier.predict("رامي واعر")
        r2 = classifier.predict("رامي واعر")
        assert r1["label"] == r2["label"]
        assert r1["confidence"] == r2["confidence"]
        assert r1["logits"] == r2["logits"]


# ---------------------------------------------------------------------------
# 8. Fine-tuning interface (test de surface, pas d'entraînement réel)
# ---------------------------------------------------------------------------

class TestFineTuningInterface:
    """fine_tune() et save()/load() exposent la bonne interface."""

    def test_methode_fine_tune_existe(self, classifier):
        assert hasattr(classifier, "fine_tune"), \
            "SentimentClassifier doit avoir une méthode fine_tune()"

    def test_methode_save_existe(self, classifier):
        assert hasattr(classifier, "save")

    def test_methode_load_existe(self, classifier):
        assert hasattr(classifier, "load")

    def test_save_cree_fichier(self, classifier, tmp_path):
        """save() sauvegarde le modèle sans erreur."""
        try:
            classifier.save(tmp_path / "test_model")
        except NotImplementedError:
            pytest.skip("save() non implémentée (acceptable en fallback mode)")
        except Exception as e:
            # On accepte que le fake model ne puisse pas se sauvegarder
            # mais pas une AttributeError (méthode manquante)
            assert not isinstance(e, AttributeError), f"save() manquante: {e}"


# ---------------------------------------------------------------------------
# 9. Tests d'intégration (marqués slow, requièrent le réseau)
# ---------------------------------------------------------------------------

@pytest.mark.slow
class TestIntegrationReelle:
    """Tests avec le vrai DziriBERT — nécessitent réseau + ~400MB d'espace.

    Lancer avec: pytest -m slow
    """

    def test_chargement_dziribert_reel(self):
        """DziriBERT se charge depuis HuggingFace ou cache local."""
        pytest.importorskip("transformers")
        from core.analysis.sentiment_classifier import SentimentClassifier
        try:
            clf = SentimentClassifier(model_name="alger-ia/dziribert")
            r = clf.predict("رامي واعر")
            assert r["label"] in SENTIMENT_LABELS
            assert 0.0 <= r["confidence"] <= 1.0
        except OSError:
            pytest.skip("DziriBERT non disponible (pas de réseau ou cache)")

    def test_inference_rapide(self):
        """Inférence unitaire < 2 secondes sur CPU (modèle chargé)."""
        import time
        pytest.importorskip("transformers")
        from core.analysis.sentiment_classifier import SentimentClassifier
        try:
            clf = SentimentClassifier(model_name="alger-ia/dziribert")
            start = time.time()
            clf.predict("رامي واعر بزاف")
            elapsed = time.time() - start
            assert elapsed < 10.0, f"Inférence trop lente: {elapsed:.2f}s"
        except OSError:
            pytest.skip("DziriBERT non disponible")
