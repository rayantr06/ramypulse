"""Moteur de simulation What-If pour recalculer le NSS par aspect.

Permet de répondre à la question : « Si on améliore l'emballage, quel impact sur le NSS ? »
"""
import logging

import pandas as pd

from core.analysis.nss_calculator import calculate_nss, calculate_nss_by_channel

logger = logging.getLogger(__name__)

# Scénarios autorisés
SCENARIOS_VALIDES = {"neutraliser", "améliorer", "dégrader"}

# Remapping pour le scénario "améliorer" : chaque classe monte d'un cran
REMAPPING_AMELIORER: dict[str, str] = {
    "très_négatif": "négatif",
    "négatif": "neutre",
    "neutre": "positif",
    "positif": "très_positif",
    "très_positif": "très_positif",  # déjà au maximum
}

# Remapping pour le scénario "dégrader" : chaque classe descend d'un cran
REMAPPING_DEGRADER: dict[str, str] = {
    "très_positif": "positif",
    "positif": "neutre",
    "neutre": "négatif",
    "négatif": "très_négatif",
    "très_négatif": "très_négatif",  # déjà au minimum
}


def _build_aspect_mask(dataframe: pd.DataFrame, aspect: str) -> pd.Series:
    """Construit un masque compatible avec une colonne aspect scalaire ou aspects liste."""
    if "aspects" in dataframe.columns:
        return dataframe["aspects"].apply(
            lambda value: isinstance(value, (list, tuple, set)) and aspect in value
        )
    if "aspect" not in dataframe.columns:
        return pd.Series(False, index=dataframe.index)
    return dataframe["aspect"] == aspect


def simulate(aspect: str, scenario: str, df: pd.DataFrame) -> dict:
    """Simule l'impact d'un scénario What-If sur le NSS global.

    Algorithme :
    1. Copier le DataFrame (ne jamais modifier l'original).
    2. Identifier les enregistrements de l'aspect ciblé.
    3. Appliquer le scénario (neutraliser / améliorer / dégrader).
    4. Recalculer le NSS sur le DataFrame modifié.
    5. Calculer le delta et générer l'interprétation.

    Args:
        aspect: Aspect produit ciblé (goût, emballage, prix, disponibilité, fraîcheur).
        scenario: Scénario de simulation — 'neutraliser', 'améliorer' ou 'dégrader'.
        df: DataFrame ABSA complet avec les colonnes standard RamyPulse.

    Returns:
        Dict avec les clés :
          - nss_actuel (float)
          - nss_simule (float)
          - delta (float)
          - interpretation (str)
          - affected_count (int)
          - nss_by_channel_simulated (dict)

    Raises:
        ValueError: Si le scénario n'est pas reconnu.
    """
    if scenario not in SCENARIOS_VALIDES:
        raise ValueError(
            f"Scénario invalide : '{scenario}'. "
            f"Valeurs acceptées : {sorted(SCENARIOS_VALIDES)}"
        )

    # 1. Copier le DataFrame — ne jamais modifier l'original
    df_sim = df.copy()

    # 2. NSS avant simulation
    nss_actuel = calculate_nss(df)["nss_global"]

    # 3. Identifier les enregistrements de l'aspect ciblé
    mask_aspect = _build_aspect_mask(df_sim, aspect)
    affected_count = int(mask_aspect.sum())

    # Cas particulier : aucun enregistrement pour cet aspect
    if affected_count == 0:
        logger.warning("What-If : l'aspect '%s' est absent des données.", aspect)
        return {
            "nss_actuel": nss_actuel,
            "nss_simule": nss_actuel,
            "delta": 0.0,
            "interpretation": (
                f"L'aspect '{aspect}' n'a aucun enregistrement dans les données. "
                "Aucun impact simulé."
            ),
            "affected_count": 0,
            "nss_by_channel_simulated": calculate_nss_by_channel(df_sim),
        }

    # 4. Appliquer le scénario
    if scenario == "neutraliser":
        # Supprimer les enregistrements de cet aspect du calcul
        df_sim = df_sim[~mask_aspect].reset_index(drop=True)
    elif scenario == "améliorer":
        df_sim.loc[mask_aspect, "sentiment_label"] = (
            df_sim.loc[mask_aspect, "sentiment_label"].map(REMAPPING_AMELIORER)
        )
    else:  # dégrader
        df_sim.loc[mask_aspect, "sentiment_label"] = (
            df_sim.loc[mask_aspect, "sentiment_label"].map(REMAPPING_DEGRADER)
        )

    # 5. Recalculer le NSS sur le DataFrame modifié
    nss_simule = calculate_nss(df_sim)["nss_global"]
    delta = round(nss_simule - nss_actuel, 2)

    # 6. Générer l'interprétation
    interpretation = _generer_interpretation(aspect, scenario, delta)

    nss_by_channel_simulated = calculate_nss_by_channel(df_sim)

    logger.info(
        "What-If [%s / %s] : NSS %+.1f → %+.1f (Δ%+.1f) — %d avis affectés",
        aspect,
        scenario,
        nss_actuel,
        nss_simule,
        delta,
        affected_count,
    )

    return {
        "nss_actuel": nss_actuel,
        "nss_simule": nss_simule,
        "delta": delta,
        "interpretation": interpretation,
        "affected_count": affected_count,
        "nss_by_channel_simulated": nss_by_channel_simulated,
    }


def simulate_whatif(aspect: str, scenario: str, df: pd.DataFrame) -> dict:
    """Alias rétrocompatible vers l'API PRD ``simulate``."""
    return simulate(aspect, scenario, df)


def _generer_interpretation(aspect: str, scenario: str, delta: float) -> str:
    """Génère une phrase d'interprétation lisible pour l'utilisateur.

    Args:
        aspect: Aspect ciblé par la simulation.
        scenario: Scénario appliqué.
        delta: Différence nss_simule - nss_actuel.

    Returns:
        Chaîne de caractères décrivant l'impact de la simulation.
    """
    delta_abs = abs(delta)

    if scenario == "neutraliser":
        if delta > 0:
            return (
                f"La suppression des avis '{aspect}' augmenterait le NSS "
                f"de {delta_abs:.1f} points."
            )
        if delta < 0:
            return (
                f"La suppression des avis '{aspect}' diminuerait le NSS "
                f"de {delta_abs:.1f} points."
            )
        return f"La suppression des avis '{aspect}' n'aurait aucun impact sur le NSS."

    if scenario == "améliorer":
        if delta > 0:
            return (
                f"L'amélioration de {aspect} augmenterait le NSS "
                f"de {delta_abs:.1f} points."
            )
        if delta < 0:
            return (
                f"Malgré l'amélioration de {aspect}, le NSS diminuerait "
                f"de {delta_abs:.1f} points."
            )
        return f"L'amélioration de {aspect} n'aurait pas d'impact significatif sur le NSS."

    # scenario == "dégrader"
    if delta < 0:
        return (
            f"La dégradation de {aspect} diminuerait le NSS "
            f"de {delta_abs:.1f} points."
        )
    if delta > 0:
        return (
            f"Malgré la dégradation de {aspect}, le NSS augmenterait "
            f"de {delta_abs:.1f} points."
        )
    return f"La dégradation de {aspect} n'aurait pas d'impact significatif sur le NSS."
