"""
Pipeline de sentiment RamyPulse — DziriBERT + détection d'incongruité + LLM arbitrage.

Architecture (inspirée de la Sentiment Incongruity Detection, cf. SAIDS / ArSarcasm-v2) :

    ┌─────────────┐
    │  Commentaire │
    └──────┬──────┘
           │
    ┌──────▼──────┐
    │  DziriBERT  │──── conf ≥ seuil ET pas de conflit ──── ▶ RÉSULTAT DIRECT
    │  (full text) │                                          (95% des cas)
    └──────┬──────┘
           │ conf ≥ seuil MAIS positif/négatif à vérifier
           │
    ┌──────▼──────────────┐
    │  Incongruity Check  │  DziriBERT sur moitié_1 vs moitié_2
    │  (split & compare)  │  Détecte les retournements de polarité
    └──────┬──────────────┘
           │ incongruité détectée (moitié_1 ≠ moitié_2)
           │
    ┌──────▼──────┐
    │  LLM Arbiter│  Gemini Flash — prompt spécialisé sarcasme/ironie
    │  (fallback)  │  Ne traite que ~2-5% du trafic
    └─────────────┘

Pourquoi cette approche :
- La littérature SOTA (SarcasmBench 2024) montre que les LLMs sous-performent
  les modèles supervisés pour la détection de sarcasme brute.
- MAIS les LLMs excellent sur l'arbitrage quand on leur donne le contexte du conflit.
- Le split+compare utilise DziriBERT lui-même comme détecteur d'incongruité
  (pas de liste de marqueurs hardcodée = pas de maintenance).
- Gemini Flash à 0.15$/1M tokens = coût négligeable sur 2-5% du trafic.

Usage Colab :
    from inference.pipeline import SentimentPipeline
    pipe = SentimentPipeline(model_dir="...", gemini_api_key="...")
    result = pipe.predict("j'adore comment Ramy met autant de sucre")
    # → {"label": "negative", "confidence": 0.92, "method": "llm_arbitrage"}

Usage production (sans Gemini) :
    pipe = SentimentPipeline(model_dir="...", gemini_api_key=None)
    # → Tourne en mode DziriBERT pur + flag incongruité
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

try:
    import google.generativeai as genai
except ImportError:
    genai = None

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────

LABEL2ID = {"positive": 0, "negative": 1, "neutral": 2}
ID2LABEL = {v: k for k, v in LABEL2ID.items()}

# Seuils pour le pipeline
CONFIDENCE_FLOOR = 0.55          # En dessous → toujours vérifier
INCONGRUITY_CHECK_LABELS = {     # Labels qui méritent une vérification
    "positive",                   # Positif peut cacher du sarcasme
    "negative",                   # Négatif peut être un faux négatif
}
MIN_TEXT_LEN_FOR_SPLIT = 20      # Textes trop courts → pas de split

# Prompt LLM pour l'arbitrage
_LLM_ARBITRAGE_PROMPT = """Tu es un expert en analyse de sentiment pour les commentaires algériens sur les boissons (Ramy, Hamoud Boualem, etc.).

Un modèle DziriBERT a classé ce commentaire comme "{dziribert_label}" (confiance: {dziribert_conf:.0%}).
MAIS une analyse interne a détecté une INCONGRUITÉ de polarité :
- Première partie du texte → {half1_label} ({half1_conf:.0%})
- Seconde partie du texte → {half2_label} ({half2_conf:.0%})

Cela peut indiquer du sarcasme, de l'ironie, ou un retournement de sens.

Commentaire complet :
"{text}"

Classe ce commentaire dans exactement UNE des 3 classes : positive, negative, neutral.
Considère le sarcasme algérien (Derja) : les gens disent parfois "ممتاز" ou "bravo" ou "j'adore" de manière ironique.
Considère aussi les retournements : phrase positive suivie d'un twist négatif = négatif.

Réponds UNIQUEMENT en JSON : {{"label": "...", "confidence": 0.0, "reasoning": "..."}}"""


# ─────────────────────────────────────────────────────────────────────
# Data structures
# ─────────────────────────────────────────────────────────────────────

@dataclass
class PredictionResult:
    """Résultat complet d'une prédiction du pipeline."""
    label: str
    confidence: float
    method: str                          # "dziribert_direct" | "incongruity_check" | "llm_arbitrage"
    distribution: dict = field(default_factory=dict)  # {label: prob}
    incongruity: Optional[dict] = None   # Détails si incongruité détectée
    llm_reasoning: Optional[str] = None  # Explication LLM si arbitrage

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
        gemini_model: str = "gemini-2.0-flash",
        device: Optional[str] = None,
        confidence_floor: float = CONFIDENCE_FLOOR,
        max_length: int = 128,
    ):
        """
        Args:
            model_dir: Chemin vers le modèle DziriBERT fine-tuné.
            gemini_api_key: Clé API Gemini. Si None, tourne en mode local pur
                            (DziriBERT + flag incongruité, sans arbitrage LLM).
            gemini_model: Modèle Gemini à utiliser pour l'arbitrage.
            device: "cuda" ou "cpu". Auto-détecté si None.
            confidence_floor: Seuil de confiance minimum pour skip l'incongruity check.
            max_length: Longueur max de tokenisation.
        """
        if AutoTokenizer is None:
            raise ImportError("transformers est requis : pip install transformers")

        self.device = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))
        self.max_length = max_length
        self.confidence_floor = confidence_floor

        # ── Charger DziriBERT ──
        logger.info("Chargement DziriBERT depuis %s", model_dir)
        self.tokenizer = AutoTokenizer.from_pretrained(model_dir)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_dir)
        self.model.to(self.device)
        self.model.eval()

        # ── Configurer Gemini (optionnel) ──
        self.gemini_model_name = gemini_model
        self._gemini_available = False
        if gemini_api_key and genai is not None:
            genai.configure(api_key=gemini_api_key)
            self._gemini = genai.GenerativeModel(gemini_model)
            self._gemini_available = True
            logger.info("LLM arbitrage activé : %s", gemini_model)
        else:
            self._gemini = None
            if gemini_api_key and genai is None:
                logger.warning("google-generativeai non installé. Mode local pur.")
            elif not gemini_api_key:
                logger.info("Pas de clé Gemini. Mode local pur (DziriBERT + flag incongruité).")

        # ── Compteurs ──
        self.stats = {"total": 0, "direct": 0, "incongruity_checked": 0, "llm_arbitrated": 0}

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

        # Neutral avec bonne confiance → direct (le sarcasme neutral est quasi inexistant)
        if full_pred["label"] == "neutral" and full_pred["confidence"] >= self.confidence_floor:
            self.stats["direct"] += 1
            return PredictionResult(
                label=full_pred["label"],
                confidence=full_pred["confidence"],
                method="dziribert_direct",
                distribution=full_pred["distribution"],
            )

        # Confiance très haute → probablement correct
        if full_pred["confidence"] >= 0.95:
            # Même à haute confiance, on vérifie les positifs
            # car ADV-04 (merci+plastique) et ADV-18 (نشكر ربي) → 0.99 positif erroné
            # SAUF si le texte est trop court pour être sarcastique
            if full_pred["label"] != "positive" or len(text) < MIN_TEXT_LEN_FOR_SPLIT:
                self.stats["direct"] += 1
                return PredictionResult(
                    label=full_pred["label"],
                    confidence=full_pred["confidence"],
                    method="dziribert_direct",
                    distribution=full_pred["distribution"],
                )

        # ── Étape 2 : Incongruity check (split & compare) ──
        if len(text) >= MIN_TEXT_LEN_FOR_SPLIT and full_pred["label"] in INCONGRUITY_CHECK_LABELS:
            incongruity = self._check_incongruity(text, full_pred)
            self.stats["incongruity_checked"] += 1

            if incongruity["detected"]:
                # ── Étape 3 : LLM arbitrage (si disponible) ──
                if self._gemini_available:
                    self.stats["llm_arbitrated"] += 1
                    return self._llm_arbitrate(text, full_pred, incongruity)

                # Mode local : renvoyer le résultat DziriBERT + flag incongruité
                return PredictionResult(
                    label=full_pred["label"],
                    confidence=full_pred["confidence"] * 0.7,  # Pénaliser la confiance
                    method="incongruity_flagged",
                    distribution=full_pred["distribution"],
                    incongruity=incongruity,
                )

        # Pas d'incongruité → résultat DziriBERT direct
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

    # ─── Incongruity detection ───────────────────────────────────

    def _split_text(self, text: str) -> tuple[str, str]:
        """Découpe le texte en 2 moitiés sémantiques.

        Stratégie : cherche un séparateur naturel (virgule, point, بصح, mais, mais, w )
        près du milieu. Sinon, coupe au milieu sur un espace.
        """
        # Séparateurs sémantiques (algérien + français)
        separators = [
            r'،',           # virgule arabe
            r',',           # virgule latine
            r'\.',          # point
            r'\bبصح\b',     # "mais" en Derja
            r'\bمع ذلك\b',   # "cependant" en arabe
            r'\bmais\b',    # français
            r'\bw\b',       # "et" en Arabizi (souvent marque un pivot)
            r'\bبصراحة\b',   # "franchement"
        ]

        mid = len(text) // 2
        best_pos = None
        best_dist = len(text)

        for sep in separators:
            for match in re.finditer(sep, text, re.IGNORECASE):
                pos = match.start()
                dist = abs(pos - mid)
                if dist < best_dist and pos > 5 and pos < len(text) - 5:
                    best_dist = dist
                    best_pos = pos

        if best_pos is not None and best_dist < len(text) * 0.4:
            return text[:best_pos].strip(), text[best_pos:].strip()

        # Fallback : couper au milieu sur un espace
        space_pos = text.find(' ', mid)
        if space_pos == -1:
            space_pos = mid
        return text[:space_pos].strip(), text[space_pos:].strip()

    def _check_incongruity(self, text: str, full_pred: dict) -> dict:
        """Détecte une incongruité de polarité entre les 2 moitiés du texte."""
        half1, half2 = self._split_text(text)

        # Si une moitié est trop courte, pas d'incongruity check fiable
        if len(half1) < 5 or len(half2) < 5:
            return {"detected": False, "reason": "halves_too_short"}

        pred1 = self._dziribert_predict(half1)
        pred2 = self._dziribert_predict(half2)

        # Incongruité = les 2 moitiés ont des polarités OPPOSÉES
        polarity_conflict = (
            (pred1["label"] == "positive" and pred2["label"] == "negative")
            or (pred1["label"] == "negative" and pred2["label"] == "positive")
        )

        # Incongruité aussi si une moitié contredit la prédiction globale
        half_contradicts_full = (
            (full_pred["label"] == "positive" and pred2["label"] == "negative" and pred2["confidence"] >= 0.5)
            or (full_pred["label"] == "negative" and pred2["label"] == "positive" and pred2["confidence"] >= 0.5)
        )

        detected = polarity_conflict or half_contradicts_full

        return {
            "detected": detected,
            "half1": {"text": half1[:50], "label": pred1["label"], "confidence": round(pred1["confidence"], 3)},
            "half2": {"text": half2[:50], "label": pred2["label"], "confidence": round(pred2["confidence"], 3)},
            "polarity_conflict": polarity_conflict,
            "half_contradicts_full": half_contradicts_full,
        }

    # ─── LLM arbitrage ───────────────────────────────────────────

    def _llm_arbitrate(self, text: str, full_pred: dict, incongruity: dict) -> PredictionResult:
        """Appelle Gemini Flash pour arbitrer un cas d'incongruité."""
        prompt = _LLM_ARBITRAGE_PROMPT.format(
            text=text,
            dziribert_label=full_pred["label"],
            dziribert_conf=full_pred["confidence"],
            half1_label=incongruity["half1"]["label"],
            half1_conf=incongruity["half1"]["confidence"],
            half2_label=incongruity["half2"]["label"],
            half2_conf=incongruity["half2"]["confidence"],
        )

        try:
            response = self._gemini.generate_content(prompt)
            raw = response.text.strip()

            # Extraire le JSON de la réponse (peut être entouré de markdown)
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
            # Fallback : DziriBERT avec confiance pénalisée
            return PredictionResult(
                label=full_pred["label"],
                confidence=full_pred["confidence"] * 0.7,
                method="llm_arbitrage_failed",
                distribution=full_pred["distribution"],
                incongruity=incongruity,
            )
