"""Interface Streamlit de chat RAG avec provenance pour RamyPulse."""

from __future__ import annotations

import logging
from pathlib import Path

import streamlit as st

logger = logging.getLogger(__name__)

_EXAMPLE_QUESTIONS = [
    "Que pensent les clients de l'emballage Ramy?",
    "Quels sont les principaux problèmes remontés?",
    "Comment est perçu le prix du jus Ramy Premium?",
]

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


@st.cache_resource(show_spinner=False)
def _load_runtime() -> dict:
    """Charge le runtime RAG réel ou bascule vers un mode démo."""
    try:
        import config
        from core.rag.embedder import Embedder
        from core.rag.generator import Generator
        from core.rag.retriever import Retriever
        from core.rag.vector_store import VectorStore
    except Exception as exc:  # pragma: no cover - dépend des libs installées
        logger.warning("Chargement des modules RAG impossible: %s", exc)
        return {"mode": "demo", "reason": str(exc)}

    index_path = Path(getattr(config, "FAISS_INDEX_PATH", Path("data") / "embeddings" / "faiss_index"))
    faiss_path = index_path.with_suffix(".faiss")
    metadata_path = index_path.with_suffix(".json")

    if not faiss_path.exists() or not metadata_path.exists():
        reason = f"Index FAISS absent: {faiss_path.name} / {metadata_path.name}"
        logger.info(reason)
        return {"mode": "demo", "reason": reason}

    try:
        vector_store = VectorStore.load(str(index_path))
        retriever = Retriever(vector_store=vector_store, embedder=Embedder())
        generator = Generator()
        backend_label = generator.describe_backend()
        return {
            "mode": "live",
            "retriever": retriever,
            "generator": generator,
            "backend_label": backend_label,
            "reason": None,
        }
    except Exception as exc:  # pragma: no cover - dépend de l'environnement local
        logger.warning("Initialisation RAG réelle impossible: %s", exc)
        return {"mode": "demo", "reason": str(exc)}


def _ensure_session_state() -> None:
    """Initialise l'état de session nécessaire à l'interface de chat."""
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []
    if "pending_question" not in st.session_state:
        st.session_state["pending_question"] = None


def _set_pending_question(question: str) -> None:
    """Enregistre une question exemple à injecter dans le prochain tour."""
    st.session_state["pending_question"] = question


def _consume_question() -> str | None:
    """Récupère la prochaine question depuis un exemple ou la chat_input."""
    pending = st.session_state.pop("pending_question", None)
    typed = st.chat_input("Posez votre question sur les avis clients Ramy...")
    return pending or typed


def _render_header(mode: str, reason: str | None, backend_label: str | None = None) -> None:
    """Affiche l'en-tête principal de la page et l'état du backend."""
    st.title("Chat RAG RamyPulse")
    st.caption("Questions-réponses avec provenance à partir des avis et extraits collectés.")

    if mode == "live":
        label = backend_label or "backend RAG"
        st.success(f"Mode réel activé : retrieval hybride + génération {label}.")
    else:
        message = "Mode DEMO activé : backend RAG indisponible ou index non construit."
        if reason:
            message += f" Cause détectée : {reason}"
        st.info(message)


def _render_example_questions() -> None:
    """Affiche des questions exemples pour amorcer la conversation."""
    st.write("Exemples de questions")
    columns = st.columns(len(_EXAMPLE_QUESTIONS))
    for index, question in enumerate(_EXAMPLE_QUESTIONS):
        with columns[index]:
            st.button(
                question,
                key=f"example-question-{index}",
                use_container_width=True,
                on_click=_set_pending_question,
                args=(question,),
            )


def _retrieve_chunks(runtime: dict, question: str, top_k: int = 5) -> list[dict]:
    """Récupère les chunks pertinents en mode réel ou en mode démo."""
    if runtime["mode"] == "live":
        try:
            retriever = runtime["retriever"]
            if hasattr(retriever, "retrieve"):
                return retriever.retrieve(question, top_k=top_k)
            if hasattr(retriever, "search"):
                return retriever.search(question, top_k=top_k)
        except Exception as exc:  # pragma: no cover - dépend du backend local
            logger.warning("Retrieval réel indisponible, bascule démo: %s", exc)
    return _build_demo_chunks(question, top_k=top_k)


def _generate_answer(runtime: dict, question: str, chunks: list[dict]) -> dict:
    """Génère une réponse en mode réel ou une réponse démo réaliste."""
    if runtime["mode"] == "live":
        try:
            generator = runtime["generator"]
            if hasattr(generator, "generate"):
                return generator.generate(question, chunks)
        except Exception as exc:  # pragma: no cover - dépend du backend local
            logger.warning("Génération réelle indisponible, bascule démo: %s", exc)
    return _build_demo_answer(question, chunks)


def _build_demo_chunks(question: str, top_k: int = 5) -> list[dict]:
    """Construit des chunks de démonstration cohérents avec la question."""
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
    """Construit une réponse de démonstration réaliste avec sources."""
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
            {
                "channel": chunk.get("channel", ""),
                "url": chunk.get("url", ""),
                "timestamp": chunk.get("timestamp", ""),
            }
            for chunk in chunks[: min(2, len(chunks))]
        ],
        "confidence": confidence,
    }


def _select_display_sources(chunks: list[dict], response: dict) -> list[dict]:
    """Sélectionne les sources à afficher sous la réponse assistant."""
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


def _confidence_badge(confidence: str) -> str:
    """Retourne un badge HTML coloré pour le niveau de confiance."""
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
    """Retourne un badge HTML pour le canal de provenance."""
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


def _render_source_expanders(chunks: list[dict]) -> None:
    """Affiche les sources détaillées sous forme d'expanders."""
    for index, chunk in enumerate(chunks, start=1):
        title = f"Source {index} • {chunk.get('channel', 'inconnu')}"
        with st.expander(title):
            st.markdown(_channel_badge(chunk.get("channel", "")), unsafe_allow_html=True)
            st.write(chunk.get("text", ""))

            url = chunk.get("url", "")
            timestamp = chunk.get("timestamp", "")
            if url:
                st.markdown(f"[Ouvrir la source]({url})")
            elif timestamp:
                st.caption(f"Timestamp audio : {timestamp}")

            score = chunk.get("score")
            if score is not None:
                st.caption(f"Score de pertinence : {score}")


def _append_history(question: str, response: dict, sources: list[dict], mode: str) -> None:
    """Ajoute un échange complet dans l'historique de session."""
    st.session_state["chat_history"].append(
        {
            "question": question,
            "answer": response.get("answer", ""),
            "confidence": response.get("confidence", "low"),
            "sources": sources,
            "mode": mode,
        }
    )


def _render_history() -> None:
    """Affiche tout l'historique de conversation stocké en session."""
    for item in st.session_state["chat_history"]:
        with st.chat_message("user"):
            st.write(item["question"])

        with st.chat_message("assistant"):
            st.write(item["answer"])
            st.markdown(_confidence_badge(item["confidence"]), unsafe_allow_html=True)
            if item["mode"] == "demo":
                st.caption("Réponse générée en mode démonstration.")
            _render_source_expanders(item["sources"])


def main() -> None:
    """Construit la page de chat RAG RamyPulse."""
    _ensure_session_state()

    runtime = _load_runtime()
    _render_header(runtime["mode"], runtime.get("reason"), runtime.get("backend_label"))
    _render_example_questions()
    _render_history()

    question = _consume_question()
    if not question:
        return

    with st.chat_message("user"):
        st.write(question)

    with st.chat_message("assistant"):
        with st.spinner("Analyse des avis en cours..."):
            chunks = _retrieve_chunks(runtime, question, top_k=5)
            response = _generate_answer(runtime, question, chunks)
            display_sources = _select_display_sources(chunks, response)

        st.write(response.get("answer", ""))
        st.markdown(_confidence_badge(response.get("confidence", "low")), unsafe_allow_html=True)
        if runtime["mode"] == "demo":
            st.caption("Réponse générée en mode démonstration.")
        _render_source_expanders(display_sources)

    _append_history(question, response, display_sources, runtime["mode"])


main()
