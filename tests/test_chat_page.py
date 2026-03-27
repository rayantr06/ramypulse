"""Tests pour la logique métier de pages/03_chat.py.

Teste les fonctions pures (pas le rendu Streamlit).
Les fonctions sont copiées ici car le module Streamlit ne peut pas
être importé directement en contexte de test (exécute main() à l'import).
"""

# ---------------------------------------------------------------------------
# Données de démonstration (identiques au module source)
# ---------------------------------------------------------------------------

_DEMO_CHUNKS = [
    {
        "text": "Plusieurs avis Facebook mentionnent que l'emballage fuit parfois après ouverture.",
        "channel": "facebook",
        "url": "https://facebook.example/ramy-emballage",
        "timestamp": "2026-01-12T10:30:00",
        "score": 0.0321,
    },
    {
        "text": "Des commentaires Google Maps jugent le goût globalement bon, mais le prix est parfois jugé élevé.",
        "channel": "google_maps",
        "url": "https://maps.example/ramy-premium",
        "timestamp": "2026-01-14T15:20:00",
        "score": 0.0294,
    },
    {
        "text": "Dans les extraits audio de démonstration, la fraîcheur est perçue positivement quand le produit est servi froid.",
        "channel": "audio",
        "url": "",
        "timestamp": "00:01:42",
        "score": 0.0276,
    },
]


# ---------------------------------------------------------------------------
# Fonctions pures copiées du module 03_chat.py pour test isolé
# ---------------------------------------------------------------------------

def _confidence_badge(confidence: str) -> str:
    """Badge HTML pour le niveau de confiance."""
    mapping = {
        "high": ("🟢", "#0f766e", "#ccfbf1", "haute"),
        "medium": ("🟡", "#b45309", "#fef3c7", "moyenne"),
        "low": ("🔴", "#b91c1c", "#fee2e2", "basse"),
    }
    icon, text_color, background, label = mapping.get(confidence, mapping["low"])
    return (
        f"<span style='display:inline-block;padding:0.3rem 0.65rem;border-radius:999px;"
        f"background:{background};color:{text_color};font-weight:600;'>"
        f"{icon} Confiance {label}</span>"
    )


def _channel_badge(channel: str) -> str:
    """Badge HTML pour le canal de provenance."""
    palette = {
        "facebook": ("#1d4ed8", "#dbeafe"),
        "google_maps": ("#166534", "#dcfce7"),
        "audio": ("#7c2d12", "#ffedd5"),
        "youtube": ("#991b1b", "#fee2e2"),
    }
    text_color, background = palette.get(channel, ("#374151", "#e5e7eb"))
    return (
        f"<span style='display:inline-block;padding:0.2rem 0.55rem;border-radius:999px;"
        f"background:{background};color:{text_color};font-weight:600;'>{channel}</span>"
    )


def _build_demo_chunks(question: str, top_k: int = 5) -> list[dict]:
    """Sélection de chunks démo selon la question."""
    lowered = question.lower()
    ranked = list(_DEMO_CHUNKS)
    if "emballage" in lowered:
        ranked = [ranked[0], ranked[1], ranked[2]]
    elif "prix" in lowered:
        ranked = [ranked[1], ranked[0], ranked[2]]
    elif "probl" in lowered:
        ranked = [ranked[0], ranked[1], ranked[2]]
    return ranked[:top_k]


def _build_demo_answer(question: str, chunks: list[dict]) -> dict:
    """Réponse démo réaliste avec structure {answer, sources, confidence}."""
    lowered = question.lower()
    if "emballage" in lowered:
        answer = (
            "Les clients remontent surtout des problèmes de fuite et de solidité de l'emballage. "
            "Le sujet apparaît comme un irritant ponctuel mais visible."
        )
        confidence = "medium"
    elif "prix" in lowered:
        answer = (
            "Le prix est plutôt perçu comme acceptable sur les formats standards, mais certains avis "
            "jugent la gamme premium trop chère par rapport aux attentes."
        )
        confidence = "medium"
    elif "probl" in lowered:
        answer = (
            "Les principaux problèmes remontés concernent l'emballage, puis plus ponctuellement le prix. "
            "Le goût reste généralement mieux perçu que ces deux dimensions."
        )
        confidence = "high"
    else:
        answer = (
            "Les retours disponibles sont globalement nuancés : le goût est souvent apprécié, alors que "
            "l'emballage et le prix génèrent davantage de critiques selon les canaux."
        )
        confidence = "medium"
    return {
        "answer": answer,
        "sources": [
            {"channel": c.get("channel", ""), "url": c.get("url", ""), "timestamp": c.get("timestamp", "")}
            for c in chunks[:min(2, len(chunks))]
        ],
        "confidence": confidence,
    }


def _select_display_sources(chunks: list[dict], response: dict) -> list[dict]:
    """Sélection des sources à afficher sous la réponse."""
    cited_sources = response.get("sources") or []
    if not cited_sources:
        return chunks
    matched = []
    for source in cited_sources:
        for chunk in chunks:
            same_url = source.get("url", "") == chunk.get("url", "")
            same_channel = source.get("channel", "") == chunk.get("channel", "")
            same_timestamp = source.get("timestamp", "") == chunk.get("timestamp", "")
            if same_channel and (same_url or same_timestamp):
                matched.append(chunk)
                break
    return matched or chunks


# ===========================================================================
# TESTS
# ===========================================================================

# ---------------------------------------------------------------------------
# _confidence_badge
# ---------------------------------------------------------------------------

def test_confidence_badge_high() -> None:
    """Confiance 'high' → badge vert avec 'haute'."""
    result = _confidence_badge("high")
    assert "haute" in result
    assert "🟢" in result


def test_confidence_badge_medium() -> None:
    """Confiance 'medium' → badge jaune avec 'moyenne'."""
    result = _confidence_badge("medium")
    assert "moyenne" in result
    assert "🟡" in result


def test_confidence_badge_low() -> None:
    """Confiance 'low' → badge rouge avec 'basse'."""
    result = _confidence_badge("low")
    assert "basse" in result
    assert "🔴" in result


def test_confidence_badge_inconnu_fallback_low() -> None:
    """Valeur inconnue → fallback badge rouge."""
    result = _confidence_badge("unknown")
    assert "🔴" in result


# ---------------------------------------------------------------------------
# _channel_badge
# ---------------------------------------------------------------------------

def test_channel_badge_facebook() -> None:
    """Canal facebook → badge bleu avec 'facebook'."""
    result = _channel_badge("facebook")
    assert "facebook" in result
    assert "#1d4ed8" in result


def test_channel_badge_inconnu() -> None:
    """Canal inconnu → badge gris par défaut."""
    result = _channel_badge("inconnu")
    assert "inconnu" in result
    assert "#374151" in result


# ---------------------------------------------------------------------------
# _build_demo_chunks
# ---------------------------------------------------------------------------

def test_demo_chunks_retourne_liste_non_vide() -> None:
    """Les chunks démo sont une liste non vide."""
    chunks = _build_demo_chunks("test")
    assert isinstance(chunks, list)
    assert len(chunks) > 0


def test_demo_chunks_emballage_priorite() -> None:
    """Question sur l'emballage → premier chunk = facebook/emballage."""
    chunks = _build_demo_chunks("Que pensent les clients de l'emballage ?")
    assert chunks[0]["channel"] == "facebook"


def test_demo_chunks_prix_priorite() -> None:
    """Question sur le prix → premier chunk = google_maps."""
    chunks = _build_demo_chunks("Comment est perçu le prix ?")
    assert chunks[0]["channel"] == "google_maps"


def test_demo_chunks_top_k_respecte() -> None:
    """Le paramètre top_k limite le nombre de résultats."""
    chunks = _build_demo_chunks("test", top_k=1)
    assert len(chunks) == 1


# ---------------------------------------------------------------------------
# _build_demo_answer
# ---------------------------------------------------------------------------

def test_demo_answer_structure() -> None:
    """La réponse démo a les clés answer, sources, confidence."""
    chunks = _build_demo_chunks("test")
    result = _build_demo_answer("test", chunks)
    assert "answer" in result
    assert "sources" in result
    assert "confidence" in result


def test_demo_answer_emballage() -> None:
    """Question emballage → réponse contextuelle avec confiance medium."""
    chunks = _build_demo_chunks("emballage")
    result = _build_demo_answer("emballage", chunks)
    assert "emballage" in result["answer"].lower()
    assert result["confidence"] == "medium"


def test_demo_answer_problemes_confiance_high() -> None:
    """Question problèmes → confiance high."""
    chunks = _build_demo_chunks("problèmes")
    result = _build_demo_answer("problèmes", chunks)
    assert result["confidence"] == "high"


def test_demo_answer_sources_max_2() -> None:
    """Les sources de la réponse démo sont limitées à 2."""
    chunks = _build_demo_chunks("test")
    result = _build_demo_answer("test", chunks)
    assert len(result["sources"]) <= 2


# ---------------------------------------------------------------------------
# _select_display_sources
# ---------------------------------------------------------------------------

def test_select_sources_avec_match() -> None:
    """Les sources citées correspondent aux chunks → retour des chunks matchés."""
    chunks = _build_demo_chunks("test")
    response = _build_demo_answer("test", chunks)
    result = _select_display_sources(chunks, response)
    assert len(result) > 0


def test_select_sources_sans_sources_retourne_chunks() -> None:
    """Si pas de sources dans la réponse → retourne tous les chunks."""
    chunks = _build_demo_chunks("test")
    result = _select_display_sources(chunks, {"answer": "test", "sources": [], "confidence": "low"})
    assert result == chunks
