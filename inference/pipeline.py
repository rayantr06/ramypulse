"""
Pipeline de sentiment RamyPulse — DziriBERT + détection d'incongruité + LLM arbitrage.

Architecture (inspirée de la Sentiment Incongruity Detection, cf. SAIDS / ArSarcasm-v2) :

    ┌─────────────┐
    │  Commentaire │
    └──────┬──────┘
           │
    ┌──────▼──────┐
    │  DziriBERT  │──── neutre ou négatif direct ──── ▶ RÉSULTAT DIRECT
    │  (full text) │                                     (90-95% des cas)
    └──────┬──────┘
           │ positif avec conf ≥ 0.60 ?
           │
    ┌──────▼──────────────────────┐
    │  Incongruity Check          │  Fenêtre glissante : découpe le texte en
    │  (sliding window sentiment) │  segments, cherche un segment négatif qui
    └──────┬──────────────────────┘  contredit la prédiction positive globale
           │ segment négatif trouvé ?
           │
    ┌──────▼──────┐
    │  LLM Arbiter│  Gemini 2.5 Flash — prompt spécialisé sarcasme/ironie
    │  (fallback)  │  Ne traite que ~2-5% du trafic
    └─────────────┘

Changements v2 (fix après test réel) :
- gemini-2.0-flash → gemini-2.5-flash (2.0 déprécié, 404)
- Split en 2 moitiés → fenêtre glissante (le split ratait les cas où le mot
  positif se retrouvait dans les 2 moitiés, ex: "ممتاز ممتاز ممتاز خلاني مريض")
- Incongruity check UNIQUEMENT sur les positifs (le sarcasme inverse du positif
  vers négatif, pas l'inverse — les faux négatifs sont rares)
- Suppression du seuil 0.95 qui laissait passer ADV-04 (conf 0.99 positif erroné)
- Support des 2 SDK Gemini : ancien (google.generativeai) et nouveau (google.genai)

Usage Colab :
    from inference.pipeline import SentimentPipeline
    pipe = SentimentPipeline(model_dir="...", gemini_api_key="...")
    result = pipe.predict("j'adore comment Ramy met autant de sucre")
    # → {"label": "negative", "confidence": 0.92, "method": "llm_arbitrage"}
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Optional

import torch
import numpy as np

try:
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
except ImportError:
    AutoTokenizer = None
    AutoModelForSequenceClassification = None

# Support both old and new Gemini SDK
_genai_client = None
_genai_legacy = None

try:
    from google import genai as _genai_new_sdk
except ImportError:
    _genai_new_sdk = None

try:
    import google.generativeai as _genai_old_sdk
except ImportError:
    _genai_old_sdk = None

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────

LABEL2ID = {"positive": 0, "negative": 1, "neutral": 2}
ID2LABEL = {v: k for k, v in LABEL2ID.items()}

# Seuils
MIN_TEXT_LEN_FOR_CHECK = 15       # Textes trop courts → pas de vérification
SEGMENT_NEGATIVE_THRESHOLD = 0.50  # Un segment est "négatif" si prob neg ≥ ce seuil

# Prompt LLM
_LLM_ARBITRAGE_PROMPT = """Tu es un expert en analyse de sentiment pour les commentaires algériens sur les boissons (Ramy, Hamoud Boualem, etc.).

Un modèle DziriBERT a classé ce commentaire comme POSITIF (confiance: {dziribert_conf:.0%}).
MAIS une analyse interne a détecté une contradiction :
- Le texte global semble positif
- Mais le segment "{neg_segment}" a été détecté comme négatif ({neg_conf:.0%})
Cela peut indiquer du sarcasme, de l'ironie, ou un retournement de sens.

Commentaire complet :
"{text}"

Classe ce commentaire dans exactement UNE des 3 classes : positive, negative, neutral.
Considère le sarcasme algérien (Derja) : les gens disent parfois "ممتاز" ou "bravo" ou "j'adore" ou "merci" de manière ironique quand ils sont déçus.

Réponds UNIQUEMENT en JSON : {{"label": "...", "confidence": 0.0, "reasoning": "..."}}"""


# ─────────────────────────────────────────────────────────────────────
# Data structures
# ─────────────────────────────────────────────────────────────────────

@dataclass
class PredictionResult:
    """Résultat complet d'une prédiction du pipeline."""
    label: str
    confidence: float
    method: str                          # "dziribert_direct" | "llm_arbitrage" | "incongruity_flagged"
    distribution: dict = field(default_factory=dict)
    incongruity: Optional[dict] = None
    llm_reasoning: Optional[str] = None

    def to_dict(self) -> dict:
        d = {
            "label": self.label,
            "confidence": round(self.confidence, 4),
            "method": self.method,
            "distribution": {k: round(v, 4) for k, v in self.distribution.items()},
        }
        if self.incongruity:
            d["incongruity"] = self.incongruity
        if self.llm_reasoning:
            d["llm_reasoning"] = self.llm_reasoning
        return d


# ─────────────────────────────────────────────────────────────────────
# Pipeline
# ─────────────────────────────────────────────────────────────────────

class SentimentPipeline:
    """Pipeline de sentiment production avec détection d'incongruité."""

    def __init__(
        self,
        model_dir: str,
        gemini_api_key: Optional[str] = None,
        gemini_model: str = "gemini-2.5-flash",
        device: Optional[str] = None,
        max_length: int = 128,
    ):
        if AutoTokenizer is None:
            raise ImportError("transformers est requis : pip install transformers")

        self.device = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))
        self.max_length = max_length

        # ── Charger DziriBERT ──
        logger.info("Chargement DziriBERT depuis %s", model_dir)
        self.tokenizer = AutoTokenizer.from_pretrained(model_dir)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_dir)
        self.model.to(self.device)
        self.model.eval()

        # ── Configurer Gemini ──
        self.gemini_model_name = gemini_model
        self._gemini_available = False
        self._gemini_client = None   # new SDK
        self._gemini_legacy = None   # old SDK

        if gemini_api_key:
            if _genai_new_sdk is not None:
                try:
                    self._gemini_client = _genai_new_sdk.Client(api_key=gemini_api_key)
                    self._gemini_available = True
                    logger.info("LLM arbitrage activé (new SDK) : %s", gemini_model)
                except Exception as exc:
                    logger.warning("New genai SDK init failed (%s), trying legacy.", exc)

            if not self._gemini_available and _genai_old_sdk is not None:
                try:
                    _genai_old_sdk.configure(api_key=gemini_api_key)
                    self._gemini_legacy = _genai_old_sdk.GenerativeModel(gemini_model)
                    self._gemini_available = True
                    logger.info("LLM arbitrage activé (legacy SDK) : %s", gemini_model)
                except Exception as exc:
                    logger.warning("Legacy genai SDK init failed: %s", exc)

            if not self._gemini_available:
                logger.warning("Aucun SDK Gemini disponible. pip install google-genai ou google-generativeai")
        else:
            logger.info("Pas de clé Gemini. Mode local pur.")

        # ── Compteurs ──
        self.stats = {"total": 0, "direct": 0, "incongruity_checked": 0, "llm_arbitrated": 0, "llm_flipped": 0}

    # ─── API publique ────────────────────────────────────────────

    def predict(self, text: str) -> PredictionResult:
        """Prédit le sentiment d'un texte avec le pipeline complet."""
        self.stats["total"] += 1
        text = text.strip()
        if not text:
            return PredictionResult(
                label="neutral", confidence=1.0, method="empty_input",
                distribution={"positive": 0, "negative": 0, "neutral": 1.0},
            )

        # ── Étape 1 : DziriBERT sur le texte complet ──
        full_pred = self._dziribert_predict(text)

        # Si le modèle ne dit pas "positif" → résultat direct
        # (le sarcasme transforme du faux-positif en vrai-négatif, pas l'inverse)
        if full_pred["label"] != "positive":
            self.stats["direct"] += 1
            return PredictionResult(
                label=full_pred["label"],
                confidence=full_pred["confidence"],
                method="dziribert_direct",
                distribution=full_pred["distribution"],
            )

        # Texte trop court pour contenir du sarcasme structuré
        if len(text) < MIN_TEXT_LEN_FOR_CHECK:
            self.stats["direct"] += 1
            return PredictionResult(
                label=full_pred["label"],
                confidence=full_pred["confidence"],
                method="dziribert_direct",
                distribution=full_pred["distribution"],
            )

        # ── Étape 2 : Incongruity check (fenêtre glissante) ──
        self.stats["incongruity_checked"] += 1
        incongruity = self._check_incongruity_sliding(text, full_pred)

        if incongruity["detected"]:
            # ── Étape 3 : LLM arbitrage ──
            if self._gemini_available:
                self.stats["llm_arbitrated"] += 1
                result = self._llm_arbitrate(text, full_pred, incongruity)
                if result.label != full_pred["label"]:
                    self.stats["llm_flipped"] += 1
                return result

            # Mode local : flag l'incongruité + pénaliser la confiance
            return PredictionResult(
                label=full_pred["label"],
                confidence=full_pred["confidence"] * 0.6,
                method="incongruity_flagged",
                distribution=full_pred["distribution"],
                incongruity=incongruity,
            )

        # Pas d'incongruité → positif sincère
        self.stats["direct"] += 1
        return PredictionResult(
            label=full_pred["label"],
            confidence=full_pred["confidence"],
            method="dziribert_direct",
            distribution=full_pred["distribution"],
        )

    def predict_batch(self, texts: list[str], batch_size: int = 32) -> list[PredictionResult]:
        """Prédit le sentiment d'une liste de textes."""
        return [self.predict(text) for text in texts]

    def get_stats(self) -> dict:
        """Retourne les statistiques d'utilisation du pipeline."""
        s = self.stats.copy()
        if s["total"] > 0:
            s["direct_pct"] = round(s["direct"] / s["total"] * 100, 1)
            s["incongruity_pct"] = round(s["incongruity_checked"] / s["total"] * 100, 1)
            s["llm_pct"] = round(s["llm_arbitrated"] / s["total"] * 100, 1)
        return s

    # ─── DziriBERT inference ─────────────────────────────────────

    def _dziribert_predict(self, text: str) -> dict:
        """Inférence DziriBERT unitaire."""
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=self.max_length,
            padding=True,
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            output = self.model(**inputs)

        probs = torch.softmax(output.logits, dim=-1)[0].cpu().numpy()
        best_idx = int(np.argmax(probs))

        return {
            "label": ID2LABEL[best_idx],
            "confidence": float(probs[best_idx]),
            "distribution": {ID2LABEL[i]: float(probs[i]) for i in range(len(probs))},
        }

    # ─── Incongruity detection v2 : fenêtre glissante ────────────

    def _segment_text(self, text: str) -> list[str]:
        """Découpe le texte en segments naturels (clauses).

        Stratégie multi-niveaux :
        1. Séparer sur les ponctuations et connecteurs forts (virgule, point, بصح, mais)
        2. Si pas assez de segments, séparer sur les espaces en groupes de 4-5 mots
        """
        # Séparateurs sémantiques (algérien + français)
        split_pattern = r'[،,\.!?؟]+|\bبصح\b|\bمع ذلك\b|\bmais\b|\bبصراحة\b'
        parts = re.split(split_pattern, text, flags=re.IGNORECASE)
        segments = [p.strip() for p in parts if p and len(p.strip()) >= 5]

        # Si on a au moins 2 segments → ok
        if len(segments) >= 2:
            return segments

        # Fallback : groupes de 4 mots (fenêtre glissante avec pas de 2)
        words = text.split()
        if len(words) < 6:
            return [text]

        window_size = min(5, len(words) // 2)
        step = max(1, window_size // 2)
        segments = []
        for i in range(0, len(words) - window_size + 1, step):
            segment = " ".join(words[i:i + window_size])
            if len(segment) >= 5:
                segments.append(segment)

        return segments if segments else [text]

    def _check_incongruity_sliding(self, text: str, full_pred: dict) -> dict:
        """Détecte une incongruité par fenêtre glissante.

        Si le texte global est positif mais qu'UN segment est fortement négatif,
        c'est un signal de sarcasme ou de retournement.
        """
        segments = self._segment_text(text)

        if len(segments) < 2:
            return {"detected": False, "reason": "text_too_short", "segments": []}

        # Prédire chaque segment
        segment_preds = []
        worst_neg_score = 0.0
        worst_neg_segment = None
        worst_neg_pred = None

        for seg in segments:
            pred = self._dziribert_predict(seg)
            seg_info = {
                "text": seg[:60],
                "label": pred["label"],
                "confidence": round(pred["confidence"], 3),
                "neg_prob": round(pred["distribution"].get("negative", 0), 3),
            }
            segment_preds.append(seg_info)

            # Tracker le segment le plus négatif
            neg_prob = pred["distribution"].get("negative", 0)
            if neg_prob > worst_neg_score:
                worst_neg_score = neg_prob
                worst_neg_segment = seg
                worst_neg_pred = pred

        # Incongruité = global positif MAIS au moins un segment fortement négatif
        detected = worst_neg_score >= SEGMENT_NEGATIVE_THRESHOLD

        return {
            "detected": detected,
            "global_label": full_pred["label"],
            "global_confidence": round(full_pred["confidence"], 3),
            "worst_neg_segment": worst_neg_segment[:60] if worst_neg_segment else None,
            "worst_neg_score": round(worst_neg_score, 3),
            "num_segments": len(segments),
            "segments": segment_preds,
        }

    # ─── LLM arbitrage ───────────────────────────────────────────

    def _llm_arbitrate(self, text: str, full_pred: dict, incongruity: dict) -> PredictionResult:
        """Appelle Gemini pour arbitrer un cas d'incongruité."""
        prompt = _LLM_ARBITRAGE_PROMPT.format(
            text=text,
            dziribert_conf=full_pred["confidence"],
            neg_segment=incongruity.get("worst_neg_segment", ""),
            neg_conf=incongruity.get("worst_neg_score", 0),
        )

        try:
            raw = self._call_gemini(prompt)

            # Extraire le JSON
            json_match = re.search(r'\{[^}]+\}', raw)
            if json_match:
                parsed = json.loads(json_match.group())
            else:
                parsed = json.loads(raw)

            label = parsed.get("label", "").lower().strip()
            if label not in LABEL2ID:
                raise ValueError(f"Label LLM invalide: {label}")

            confidence = min(max(float(parsed.get("confidence", 0.7)), 0.0), 1.0)
            reasoning = parsed.get("reasoning", "")

            return PredictionResult(
                label=label,
                confidence=confidence,
                method="llm_arbitrage",
                distribution=full_pred["distribution"],
                incongruity=incongruity,
                llm_reasoning=reasoning,
            )

        except Exception as exc:
            logger.warning("LLM arbitrage échoué (%s). Fallback DziriBERT.", exc)
            return PredictionResult(
                label=full_pred["label"],
                confidence=full_pred["confidence"] * 0.6,
                method="llm_arbitrage_failed",
                distribution=full_pred["distribution"],
                incongruity=incongruity,
            )

    def _call_gemini(self, prompt: str) -> str:
        """Appelle Gemini via le SDK disponible (new ou legacy)."""
        if self._gemini_client is not None:
            # New SDK (google.genai)
            response = self._gemini_client.models.generate_content(
                model=self.gemini_model_name,
                contents=prompt,
            )
            return response.text.strip()

        if self._gemini_legacy is not None:
            # Legacy SDK (google.generativeai)
            response = self._gemini_legacy.generate_content(prompt)
            return response.text.strip()

        raise RuntimeError("Aucun SDK Gemini configuré")
