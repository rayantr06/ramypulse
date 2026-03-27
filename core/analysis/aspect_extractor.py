"""Extraction d'aspects métier pour RamyPulse."""

import re

import config

DEFAULT_ASPECT_LIST = ["goût", "emballage", "prix", "disponibilité", "fraîcheur"]
DEFAULT_ASPECT_KEYWORDS = {
    "goût": ["ta3m", "طعم", "goût", "saveur", "madha9", "bnin", "ldid", "mli7", "doux", "amer", "sucré"],
    "emballage": ["bouteille", "plastique", "تغليف", "9ar3a", "emballage", "packaging", "3olba", "couvercle", "bouchon", "fuite"],
    "prix": ["ghali", "rkhis", "سعر", "prix", "cher", "pas_cher", "prix_abordable", "t7ayol", "promotions"],
    "disponibilité": ["nlgah", "ma_kaynch", "متوفر", "disponible", "rupture", "yla9awh", "ma_lgitouch"],
    "fraîcheur": ["bared", "skhoun", "طازج", "frais", "froid", "chaud", "périmé", "fraîcheur", "date", "expiration"],
}


def _get_aspect_list() -> list[str]:
    """Retourne la liste d'aspects configurée ou la valeur par défaut."""
    return list(getattr(config, "ASPECT_LIST", DEFAULT_ASPECT_LIST))


def _get_aspect_keywords() -> dict[str, list[str]]:
    """Retourne le dictionnaire de mots-clés configuré ou la valeur par défaut."""
    return dict(getattr(config, "ASPECT_KEYWORDS", DEFAULT_ASPECT_KEYWORDS))


def _keyword_to_regex(keyword: str) -> str:
    """Convertit un mot-clé métier en motif regex robuste."""
    parts = [re.escape(part) for part in keyword.split("_")]
    body = r"[\s_-]+".join(parts)
    if re.search(r"[\u0600-\u06FF]", keyword):
        body = r"(?:ال)?" + body
    return r"(?<!\w)" + body + r"(?!\w)"


def _compile_patterns() -> dict[str, re.Pattern[str]]:
    """Compile les motifs regex pour chaque aspect supporté."""
    configured_aspects = set(_get_aspect_list())
    patterns = {}
    for aspect, keywords in _get_aspect_keywords().items():
        if aspect not in configured_aspects:
            continue
        union = "|".join(_keyword_to_regex(keyword) for keyword in keywords)
        patterns[aspect] = re.compile(union, flags=re.IGNORECASE)
    return patterns


def extract_aspects(text: str) -> list[dict[str, object]]:
    """Extrait les mentions d'aspects présentes dans un texte nettoyé."""
    if not text:
        return []

    matches = []
    for aspect, pattern in _compile_patterns().items():
        for match in pattern.finditer(text):
            matches.append(
                {
                    "aspect": aspect,
                    "mention": match.group(0),
                    "start": match.start(),
                    "end": match.end(),
                }
            )

    return sorted(matches, key=lambda item: (item["start"], item["end"], item["aspect"]))
