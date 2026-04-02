"""Assembleur de contexte pour l'agent de recommandations.

Construit le payload complet (metriques, alertes, campagnes, RAG chunks)
a partir du DataFrame annote et de SQLite, avant d'appeler le LLM.
Degrade gracieusement si les modules des autres agents sont absents.
"""

import json
import logging
from typing import Any

import pandas as pd

from config import ASPECT_LIST, FAISS_INDEX_PATH

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Importations optionnelles — modules des autres agents
# ---------------------------------------------------------------------------

try:
    from core.campaigns.campaign_manager import list_campaigns as _list_campaigns
    _HAS_CAMPAIGNS = True
except ImportError:
    _HAS_CAMPAIGNS = False
    logger.debug("core.campaigns non disponible — recent_campaigns sera vide")

try:
    from core.alerts.alert_manager import list_alerts as _list_alerts
    _HAS_ALERTS = True
except ImportError:
    _HAS_ALERTS = False
    logger.debug("core.alerts non disponible — active_alerts sera vide")

try:
    from core.watchlists.watchlist_manager import list_watchlists as _list_watchlists
    _HAS_WATCHLISTS = True
except ImportError:
    _HAS_WATCHLISTS = False
    logger.debug("core.watchlists non disponible — active_watchlists sera vide")


# ---------------------------------------------------------------------------
# Calcul NSS inline
# ---------------------------------------------------------------------------

_POSITIVE_LABELS = {"très_positif", "positif"}
_NEGATIVE_LABELS = {"négatif", "très_négatif"}


def _compute_nss(df: pd.DataFrame) -> float | None:
    """Calcule le Net Sentiment Score sur un DataFrame de signaux.

    Formule : (positifs + tres_positifs - negatifs - tres_negatifs) / total * 100.

    Args:
        df: DataFrame avec colonne 'sentiment_label'.

    Returns:
        Score NSS entre -100 et 100, ou None si le DataFrame est vide.
    """
    if df.empty:
        return None
    total = len(df)
    positives = df["sentiment_label"].isin(_POSITIVE_LABELS).sum()
    negatives = df["sentiment_label"].isin(_NEGATIVE_LABELS).sum()
    return round((positives - negatives) / total * 100, 2)


def _compute_nss_by_aspect(df: pd.DataFrame) -> dict:
    """Calcule le NSS par aspect.

    Args:
        df: DataFrame avec colonnes 'sentiment_label' et 'aspect'.

    Returns:
        Dict {aspect: nss_value}. Les aspects sans donnees ont None.
    """
    result: dict = {}
    if "aspect" not in df.columns:
        return {aspect: None for aspect in ASPECT_LIST}
    for aspect in ASPECT_LIST:
        sub = df[df["aspect"] == aspect]
        result[aspect] = _compute_nss(sub)
    return result


def _compute_nss_by_channel(df: pd.DataFrame) -> dict:
    """Calcule le NSS par canal de collecte.

    Args:
        df: DataFrame avec colonnes 'sentiment_label' et 'channel'.

    Returns:
        Dict {channel: nss_value}.
    """
    result: dict = {}
    for channel in df["channel"].dropna().unique():
        sub = df[df["channel"] == channel]
        result[str(channel)] = _compute_nss(sub)
    return result


def _top_negative_aspects(df: pd.DataFrame, n: int = 3) -> list:
    """Retourne les n aspects avec le NSS le plus faible.

    Args:
        df: DataFrame annote.
        n: Nombre d'aspects a retourner.

    Returns:
        Liste des noms d'aspects tries du NSS le plus bas.
    """
    nss_by_aspect = _compute_nss_by_aspect(df)
    scored = [(asp, nss) for asp, nss in nss_by_aspect.items() if nss is not None]
    scored.sort(key=lambda x: x[1])
    return [asp for asp, _ in scored[:n]]


# ---------------------------------------------------------------------------
# Chargement RAG optionnel
# ---------------------------------------------------------------------------

def _load_retriever() -> Any | None:
    """Tente de charger le Retriever FAISS + BM25.

    Returns:
        Retriever si l'index existe, None sinon (degrade silencieusement).
    """
    try:
        from core.rag.embedder import Embedder
        from core.rag.retriever import Retriever
        from core.rag.vector_store import VectorStore
        vs = VectorStore()
        vs.load(str(FAISS_INDEX_PATH))
        if not vs.metadata:
            logger.debug("Index FAISS vide — rag_chunks sera vide")
            return None
        return Retriever(vs, Embedder())
    except Exception as exc:
        logger.debug("Impossible de charger le RAG : %s", exc)
        return None


# ---------------------------------------------------------------------------
# Estimation tokens
# ---------------------------------------------------------------------------

def _estimate_tokens(context: dict) -> int:
    """Estime le nombre de tokens du contexte JSON serialise.

    Approximation : 1 token ~ 4 caracteres.

    Args:
        context: Dict du contexte assemble.

    Returns:
        Estimation entiere.
    """
    try:
        serialized = json.dumps(context, ensure_ascii=False, default=str)
        return max(1, len(serialized) // 4)
    except (TypeError, ValueError):
        return 0


# ---------------------------------------------------------------------------
# Requete RAG
# ---------------------------------------------------------------------------

def _build_rag_query(trigger_type: str, trigger_id: str | None, metrics: dict) -> str:
    """Construit la requete RAG a partir du declencheur et des metriques.

    Args:
        trigger_type: Type de declencheur.
        trigger_id: ID de declencheur.
        metrics: Dict des metriques courantes.

    Returns:
        Requete textuelle pour la recherche RAG.
    """
    top_negative = metrics.get("top_negative_aspects", [])
    base = "recommandations marketing Ramy"
    if top_negative:
        base += " " + " ".join(top_negative[:2]) + " problemes clients"
    if trigger_type == "alert_triggered" and trigger_id:
        base += " alerte critique"
    return base


# ---------------------------------------------------------------------------
# Interface publique
# ---------------------------------------------------------------------------

def build_recommendation_context(
    trigger_type: str,
    trigger_id: str | None,
    df_annotated: pd.DataFrame,
    max_rag_chunks: int = 8,
) -> dict:
    """Assemble le contexte complet pour l'agent de recommandations.

    Lit les alertes actives, watchlists actives et campagnes recentes depuis
    SQLite (via les managers des autres agents si disponibles). Calcule les
    metriques NSS directement depuis le DataFrame. Recupere les chunks RAG
    les plus pertinents selon le declencheur.

    Args:
        trigger_type: 'manual' | 'alert_triggered' | 'scheduled'.
        trigger_id: ID de l'alerte, watchlist ou campagne. None si global.
        df_annotated: DataFrame annote charge depuis annotated.parquet.
        max_rag_chunks: Nombre maximum de chunks RAG a inclure.

    Returns:
        Dict avec cles : client_profile, trigger, current_metrics,
        active_alerts, active_watchlists, recent_campaigns, rag_chunks,
        estimated_tokens.
    """
    context: dict = {}

    # 1. Profil client
    context["client_profile"] = {
        "client_name": "Ramy",
        "industry": "Agroalimentaire algerien",
        "main_products": ["Ramy Citron", "Ramy Orange", "Ramy Fraise", "Ramy Multivitamines"],
        "active_regions": ["alger", "oran", "constantine", "annaba", "tlemcen", "setif"],
    }

    # 2. Declencheur
    context["trigger"] = {"type": trigger_type, "id": trigger_id}

    # 3. Metriques courantes depuis le DataFrame
    nss_global = _compute_nss(df_annotated)
    nss_by_aspect = _compute_nss_by_aspect(df_annotated)
    nss_by_channel = _compute_nss_by_channel(df_annotated)
    top_neg = _top_negative_aspects(df_annotated) if not df_annotated.empty else []

    context["current_metrics"] = {
        "nss_global": nss_global,
        "nss_by_aspect": nss_by_aspect,
        "nss_by_channel": nss_by_channel,
        "volume_total": len(df_annotated),
        "top_negative_aspects": top_neg,
    }

    # 4. Alertes actives
    active_alerts: list = []
    if _HAS_ALERTS:
        try:
            all_alerts = _list_alerts(limit=100)
            active = [
                a for a in all_alerts
                if a.get("status") in ("new", "acknowledged", "investigating")
            ]
            _sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            active.sort(key=lambda a: _sev_order.get(a.get("severity", "low"), 4))
            active_alerts = active[:5]
        except Exception as exc:
            logger.warning("Erreur chargement alertes : %s", exc)

    context["active_alerts"] = active_alerts

    # 5. Watchlists actives
    active_watchlists: list = []
    if _HAS_WATCHLISTS:
        try:
            active_watchlists = _list_watchlists(is_active=True)[:5]
        except Exception as exc:
            logger.warning("Erreur chargement watchlists : %s", exc)

    context["active_watchlists"] = active_watchlists

    # 6. Campagnes recentes
    recent_campaigns: list = []
    if _HAS_CAMPAIGNS:
        try:
            recent_campaigns = _list_campaigns(limit=3)
        except Exception as exc:
            logger.warning("Erreur chargement campagnes : %s", exc)

    context["recent_campaigns"] = recent_campaigns

    # 7. Chunks RAG pertinents
    rag_chunks: list = []
    retriever = _load_retriever()
    if retriever is not None:
        try:
            query = _build_rag_query(trigger_type, trigger_id, context["current_metrics"])
            raw_chunks = retriever.search(query, top_k=max_rag_chunks)
            rag_chunks = [
                {
                    "text": c["text"],
                    "channel": c["channel"],
                    "timestamp": c["timestamp"],
                }
                for c in raw_chunks
            ]
        except Exception as exc:
            logger.warning("Erreur recuperation RAG : %s", exc)

    context["rag_chunks"] = rag_chunks

    # 8. Estimation taille contexte
    context["estimated_tokens"] = _estimate_tokens(context)

    logger.info(
        "Contexte assemble — trigger=%s alertes=%d watchlists=%d campagnes=%d chunks=%d tokens~%d",
        trigger_type,
        len(active_alerts),
        len(active_watchlists),
        len(recent_campaigns),
        len(rag_chunks),
        context["estimated_tokens"],
    )
    return context
