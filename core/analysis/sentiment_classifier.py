"""Classifieur de sentiment DziriBERT pour RamyPulse."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Union

import torch

try:
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
except Exception:  # pragma: no cover - depend de l'environnement
    AutoModelForSequenceClassification = None
    AutoTokenizer = None

from config import DZIRIBERT_MODEL_PATH, SENTIMENT_LABELS

logger = logging.getLogger(__name__)

_DEFAULT_MODEL_NAME = "alger-ia/dziribert"
_MAX_SEQ_LEN = 128
_POSITIVE_WORDS = {"bon", "bnin", "good", "mlih", "mli7", "wa3er", "frais", "excellent", "top"}
_NEGATIVE_WORDS = {"ghali", "cher", "bad", "mauvais", "khayeb", "perime", "fuite", "rupture"}


class _FallbackModelOutput:
    """Structure minimale pour exposer des logits compatibles."""

    def __init__(self, logits: torch.Tensor):
        """Initialise la sortie du modele de secours."""
        self.logits = logits


class _FallbackSequenceClassifier(torch.nn.Module):
    """Modele local minimal quand DziriBERT ne peut pas etre charge."""

    def __init__(self, num_labels: int):
        """Initialise un modele de secours deterministe."""
        super().__init__()
        self.num_labels = num_labels

    def forward(self, input_ids=None, attention_mask=None, token_type_ids=None, **kwargs):
        """Retourne des logits neutres et stables."""
        if input_ids is None:
            input_ids = torch.zeros(1, 1, dtype=torch.long)
        batch_size = input_ids.shape[0]
        logits = torch.zeros(batch_size, self.num_labels, device=input_ids.device)
        neutral_index = SENTIMENT_LABELS.index("neutre") if "neutre" in SENTIMENT_LABELS else 0
        logits[:, neutral_index] = 2.0
        return _FallbackModelOutput(logits=logits)

    def to(self, device):
        """Conserve l'API torch.nn.Module.to()."""
        return self


class _FallbackTokenizer:
    """Tokenizer minimal compatible avec le mode de secours."""

    def __call__(self, text, return_tensors="pt", truncation=True, max_length=128, padding=True):
        """Retourne des tenseurs simples pour conserver l'API."""
        if isinstance(text, str):
            texts = [text if text.strip() else "[PAD]"]
        else:
            texts = [item if item.strip() else "[PAD]" for item in text]

        token_lengths = []
        for item in texts:
            token_lengths.append(max(1, min(max_length, len(item.split()) or 1)))

        seq_len = max(token_lengths)
        batch_size = len(texts)
        input_ids = torch.zeros(batch_size, seq_len, dtype=torch.long)
        attention_mask = torch.zeros(batch_size, seq_len, dtype=torch.long)

        for index, token_len in enumerate(token_lengths):
            attention_mask[index, :token_len] = 1

        return {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "token_type_ids": torch.zeros(batch_size, seq_len, dtype=torch.long),
        }


class SentimentClassifier:
    """Classifieur de sentiment 5 classes base sur DziriBERT."""

    def __init__(
        self,
        model=None,
        tokenizer=None,
        model_name: Optional[Union[str, Path]] = None,
        device: Optional[str] = None,
    ):
        """Initialise le classifieur avec injection ou chargement pretrained."""
        self.device = self._resolve_device(device)
        self.num_labels = len(SENTIMENT_LABELS)
        self._fallback_mode = False

        if model is not None and tokenizer is not None:
            self.model = model.to(self.device)
            self.tokenizer = tokenizer
        else:
            name = str(model_name) if model_name else str(DZIRIBERT_MODEL_PATH)
            self._load_from_pretrained(name)

        if hasattr(self.model, "eval"):
            self.model.eval()

    def predict(self, text: str) -> dict:
        """Execute une inference unitaire sur un texte."""
        results = self._run_inference([text if text.strip() else "[PAD]"])
        return results[0]

    def predict_batch(self, texts: list, batch_size: int = 32) -> list:
        """Execute une inference batch sur une liste de textes."""
        if not texts:
            return []

        results = []
        for start in range(0, len(texts), batch_size):
            chunk = texts[start : start + batch_size]
            cleaned = [text if text.strip() else "[PAD]" for text in chunk]
            results.extend(self._run_inference(cleaned))
        return results

    def fine_tune(
        self,
        train_dataset,
        val_dataset,
        epochs: int = 3,
        lr: float = 2e-5,
        batch_size: int = 16,
        output_dir: Optional[Path] = None,
    ) -> dict:
        """Lance le fine-tuning HuggingFace quand l'environnement le permet."""
        try:
            from transformers import Trainer, TrainingArguments
        except ImportError as exc:
            raise ImportError(
                "fine_tune() necessite 'accelerate': pip install accelerate"
            ) from exc

        save_dir = output_dir or DZIRIBERT_MODEL_PATH
        Path(save_dir).mkdir(parents=True, exist_ok=True)

        training_args = TrainingArguments(
            output_dir=str(save_dir),
            num_train_epochs=epochs,
            per_device_train_batch_size=batch_size,
            per_device_eval_batch_size=batch_size * 2,
            learning_rate=lr,
            weight_decay=0.01,
            evaluation_strategy="epoch",
            save_strategy="epoch",
            load_best_model_at_end=True,
            metric_for_best_model="accuracy",
            logging_dir=str(Path(save_dir) / "logs"),
            no_cuda=not torch.cuda.is_available(),
        )

        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=val_dataset,
            compute_metrics=self._compute_metrics,
        )

        trainer.train()
        metrics = trainer.evaluate()
        logger.info("Fine-tuning termine: %s", metrics)
        return metrics

    def save(self, path: Union[str, Path]) -> None:
        """Sauvegarde le modele et le tokenizer quand c'est possible."""
        save_path = Path(path)
        save_path.mkdir(parents=True, exist_ok=True)

        if hasattr(self.model, "save_pretrained"):
            self.model.save_pretrained(str(save_path))
            logger.info("Modele sauvegarde dans %s", save_path)
        else:
            logger.warning("Modele factice: save() ignoree (mode test ou fallback)")

        if hasattr(self.tokenizer, "save_pretrained"):
            self.tokenizer.save_pretrained(str(save_path))

    def load(self, path: Union[str, Path]) -> None:
        """Charge un modele depuis le disque."""
        self._load_from_pretrained(str(path))
        self.model.eval()
        logger.info("Modele charge depuis %s", path)

    def _resolve_device(self, device: Optional[str]) -> torch.device:
        """Determine le device a utiliser."""
        if device:
            return torch.device(device)
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")

    def _load_from_pretrained(self, name: str) -> None:
        """Charge DziriBERT depuis le disque ou HuggingFace."""
        local_path = Path(name)
        if local_path.exists() and any(local_path.iterdir()):
            source = str(local_path)
        else:
            source = _DEFAULT_MODEL_NAME
            logger.warning(
                "Chemin local '%s' vide ou inexistant. Chargement depuis HuggingFace: %s",
                name,
                source,
            )

        if AutoTokenizer is None or AutoModelForSequenceClassification is None:
            logger.warning(
                "Transformers indisponible ou incomplet. Activation du fallback local pour %s.",
                source,
            )
            self._use_fallback_model()
            return

        try:
            logger.info("Chargement du tokenizer depuis: %s", source)
            self.tokenizer = AutoTokenizer.from_pretrained(source)

            logger.info("Chargement du modele (5 classes) depuis: %s", source)
            self.model = AutoModelForSequenceClassification.from_pretrained(
                source,
                num_labels=self.num_labels,
                ignore_mismatched_sizes=True,
            ).to(self.device)
        except Exception as exc:  # pragma: no cover - depend de HF/torch
            logger.warning(
                "Chargement DziriBERT impossible (%s). Activation du fallback local minimal.",
                exc,
            )
            self._use_fallback_model()

    def _use_fallback_model(self) -> None:
        """Active le mode de secours local."""
        self._fallback_mode = True
        self.tokenizer = _FallbackTokenizer()
        self.model = _FallbackSequenceClassifier(self.num_labels).to(self.device)

    def _run_inference(self, texts: list) -> list:
        """Execute l'inference sur une liste de textes."""
        if self._fallback_mode:
            return self._run_fallback_inference(texts)

        inputs = self.tokenizer(
            texts,
            return_tensors="pt",
            truncation=True,
            max_length=_MAX_SEQ_LEN,
            padding=True,
        )
        inputs = {
            key: value.to(self.device) if isinstance(value, torch.Tensor) else value
            for key, value in inputs.items()
        }

        with torch.no_grad():
            output = self.model(**inputs)

        logits = output.logits
        probs = torch.softmax(logits, dim=-1)

        results = []
        for index in range(logits.shape[0]):
            logits_row = logits[index].tolist()
            probs_row = probs[index].tolist()
            best_index = int(probs[index].argmax().item())
            results.append(
                {
                    "label": SENTIMENT_LABELS[best_index],
                    "confidence": float(probs_row[best_index]),
                    "logits": [float(value) for value in logits_row],
                }
            )
        return results

    def _run_fallback_inference(self, texts: list) -> list:
        """Execute une inference heuristique quand le modele reel est indisponible."""
        results = []
        neutral_index = SENTIMENT_LABELS.index("neutre") if "neutre" in SENTIMENT_LABELS else 0
        positive_index = SENTIMENT_LABELS.index("positif") if "positif" in SENTIMENT_LABELS else 0
        negative_index = SENTIMENT_LABELS.index("négatif") if "négatif" in SENTIMENT_LABELS else 0

        for text in texts:
            lowered = text.lower()
            positive_hits = sum(word in lowered for word in _POSITIVE_WORDS)
            negative_hits = sum(word in lowered for word in _NEGATIVE_WORDS)
            logits = [0.0] * self.num_labels

            target_index = neutral_index
            if positive_hits > negative_hits:
                target_index = positive_index
            elif negative_hits > positive_hits:
                target_index = negative_index

            logits[target_index] = 2.0
            tensor = torch.tensor(logits, dtype=torch.float32)
            probs = torch.softmax(tensor, dim=-1).tolist()
            results.append(
                {
                    "label": SENTIMENT_LABELS[target_index],
                    "confidence": float(probs[target_index]),
                    "logits": [float(value) for value in logits],
                }
            )

        return results

    @staticmethod
    def _compute_metrics(eval_pred) -> dict:
        """Calcule l'accuracy pour le Trainer HuggingFace."""
        logits, labels = eval_pred
        predictions = logits.argmax(axis=-1)
        accuracy = float((predictions == labels).mean())
        return {"accuracy": accuracy}


def classify_sentiment(text: str, classifier: Optional[SentimentClassifier] = None) -> dict:
    """Classifie un texte avec un classifieur fourni ou par defaut."""
    engine = classifier if classifier is not None else SentimentClassifier()
    return engine.predict(text)
