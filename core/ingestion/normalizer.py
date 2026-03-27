"""Normalisation textuelle dual-script pour le dialecte algérien.

Gère: Arabizi (chiffres phonétiques) → Arabe, texte arabe, français, mixte.
Dépendances: stdlib uniquement (re, unicodedata).
"""

import re
import unicodedata

# ---------------------------------------------------------------------------
# Tables de conversion
# ---------------------------------------------------------------------------

# Digrammes en premier (ordre décroissant de longueur) pour éviter les collisions.
# Ex: "ch" doit être converti avant "c" ou "h" séparément.
_ARABIZI_DIGRAMS: list[tuple[str, str]] = [
    ("ch", "ش"),
    ("gh", "غ"),
    ("kh", "خ"),
    ("th", "ث"),
    ("dh", "ذ"),
    ("sh", "ش"),
]

_ARABIZI_CHARS: dict[str, str] = {
    "7": "ح",
    "3": "ع",
    "9": "ق",
    "5": "خ",
    "2": "ء",
    "8": "غ",
    "6": "ط",
}

# Normalisation des graphèmes arabes
_ALEF_VARIANTS = re.compile(r"[أإآ]")
_TA_MARBUTA = re.compile(r"ة")
_YA_ALEF_MAQSURA = re.compile(r"ى")
_TATWEEL = re.compile(r"ـ")

# Plages Unicode des diacritiques arabes (tashkeel) et signes auxiliaires
_DIACRITICS = re.compile(r"[\u064B-\u065F\u0670\u06D6-\u06DC\u06DF-\u06E4\u06E7\u06E8\u06EA-\u06ED]")

# Nettoyage général
_URL = re.compile(r"https?://\S+|www\.\S+")
_MENTION = re.compile(r"@\w+")
_HASHTAG = re.compile(r"#\w+")
_MULTI_SPACE = re.compile(r" {2,}")

# Plage Unicode des emojis (simplifiée, couvre la majorité)
_EMOJI = re.compile(
    r"[\U0001F600-\U0001F64F"
    r"\U0001F300-\U0001F5FF"
    r"\U0001F680-\U0001F6FF"
    r"\U0001F700-\U0001F77F"
    r"\U0001F780-\U0001F7FF"
    r"\U0001F800-\U0001F8FF"
    r"\U0001F900-\U0001F9FF"
    r"\U0001FA00-\U0001FA6F"
    r"\U0001FA70-\U0001FAFF"
    r"\U00002702-\U000027B0"
    r"\U000024C2-\U0001F251]+",
    flags=re.UNICODE,
)

# Seuils de détection de script
_ARABIC_CHAR = re.compile(r"[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]")
_LATIN_CHAR = re.compile(r"[a-zA-Z\u00C0-\u024F]")

# Mots-clés Arabizi typiques (chiffres phonétiques)
_ARABIZI_DIGITS = re.compile(r"[73952867]")


# ---------------------------------------------------------------------------
# Fonctions internes
# ---------------------------------------------------------------------------

def _count_scripts(text: str) -> tuple[int, int]:
    """Compte les caractères arabes et latins dans le texte.

    Retourne (nb_arabic, nb_latin).
    """
    return len(_ARABIC_CHAR.findall(text)), len(_LATIN_CHAR.findall(text))


def _detect_script(text: str) -> str:
    """Détermine le script dominant: 'arabic', 'latin' ou 'mixed'.

    Un texte est 'arabic' si >70% des caractères de script sont arabes,
    'latin' si >70% sont latins, sinon 'mixed'.
    """
    nb_arabic, nb_latin = _count_scripts(text)
    total = nb_arabic + nb_latin
    if total == 0:
        return "latin"
    ratio_arabic = nb_arabic / total
    if ratio_arabic > 0.70:
        return "arabic"
    if ratio_arabic < 0.30:
        return "latin"
    return "mixed"


def _is_arabizi(text: str) -> bool:
    """Détecte si le texte contient de l'Arabizi (chiffres phonétiques + latin).

    Critère: texte majoritairement latin ET contient des chiffres phonétiques (7, 3, 9…).
    """
    nb_arabic, nb_latin = _count_scripts(text)
    total = nb_arabic + nb_latin
    if total == 0:
        return False
    is_mostly_latin = nb_latin / total > 0.50
    has_phonetic_digits = bool(_ARABIZI_DIGITS.search(text))
    return is_mostly_latin and has_phonetic_digits


def _detect_language(text: str, script: str, arabizi_detected: bool) -> str:
    """Infère la langue à partir du script et du contexte.

    Retourne: 'darija', 'french' ou 'mixed'.
    """
    if arabizi_detected:
        return "darija"
    if script == "arabic":
        return "darija"
    if script == "latin":
        return "french"
    return "mixed"


def _convert_arabizi(text: str) -> str:
    """Convertit les séquences Arabizi en caractères arabes.

    Applique d'abord les digrammes (2 caractères), puis les chiffres isolés.
    La partie latine résiduelle est mise en minuscules.
    """
    # Digrammes (insensible à la casse)
    result = text
    for digram, arabic in _ARABIZI_DIGRAMS:
        result = re.sub(re.escape(digram), arabic, result, flags=re.IGNORECASE)
    # Chiffres phonétiques
    for digit, arabic in _ARABIZI_CHARS.items():
        result = result.replace(digit, arabic)
    return result


def _normalize_arabic_graphemes(text: str) -> str:
    """Normalise les variantes graphiques arabes.

    - أإآ → ا (Alef)
    - ة → ه (Ta marbuta)
    - ى → ي (Ya / Alef maqsura)
    - Supprime le tatweel (ـ)
    - Supprime les diacritiques (tashkeel)
    """
    text = _ALEF_VARIANTS.sub("ا", text)
    text = _TA_MARBUTA.sub("ه", text)
    text = _YA_ALEF_MAQSURA.sub("ي", text)
    text = _TATWEEL.sub("", text)
    text = _DIACRITICS.sub("", text)
    return text


def _clean_noise(text: str) -> str:
    """Supprime URLs, mentions, hashtags, emojis excessifs, espaces multiples."""
    text = _URL.sub("", text)
    text = _MENTION.sub("", text)
    text = _HASHTAG.sub("", text)
    # Limite les emojis répétés à 1 occurrence
    text = _EMOJI.sub(lambda m: m.group(0)[0], text)
    text = _MULTI_SPACE.sub(" ", text)
    return text.strip()


# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------

def normalize(text: str) -> dict:
    """Normalise un texte en dialecte algérien (Arabizi, Arabe, Français, mixte).

    Algorithme:
    1. Nettoyage du bruit (URLs, mentions, hashtags, emojis excessifs).
    2. Détection du script dominant (arabe / latin / mixte).
    3. Si Arabizi détecté: conversion phonétique chiffres+digrammes → arabe.
    4. Normalisation des graphèmes arabes (alef, ta marbuta, ya, tatweel, diacritiques).
    5. Lowercase pour la partie latine résiduelle.
    6. Nettoyage final des espaces multiples.

    Args:
        text: Texte brut en entrée.

    Returns:
        dict avec les clés:
        - "normalized": texte normalisé (str)
        - "original": texte source inchangé (str)
        - "script_detected": "arabic" | "latin" | "mixed"
        - "language": "darija" | "french" | "mixed"
    """
    original = text

    if not text or not text.strip():
        return {
            "normalized": text,
            "original": original,
            "script_detected": "latin",
            "language": "french",
        }

    # Étape 1 — Nettoyage du bruit
    cleaned = _clean_noise(text)

    # Étape 2 — Détection du script (sur le texte nettoyé)
    script = _detect_script(cleaned)

    # Étape 3 — Détection Arabizi et conversion
    arabizi = _is_arabizi(cleaned)
    if arabizi:
        cleaned = _convert_arabizi(cleaned)

    # Étape 4 — Normalisation des graphèmes arabes
    cleaned = _normalize_arabic_graphemes(cleaned)

    # Étape 5 — Lowercase pour la partie latine
    # On traite chaque caractère: les caractères arabes restent inchangés
    cleaned = "".join(
        ch.lower() if ch.isascii() or unicodedata.category(ch).startswith("L")
        and not _ARABIC_CHAR.match(ch) else ch
        for ch in cleaned
    )

    # Étape 6 — Nettoyage final des espaces
    cleaned = _MULTI_SPACE.sub(" ", cleaned).strip()

    # Détection de la langue (après conversion Arabizi)
    language = _detect_language(cleaned, _detect_script(cleaned), arabizi)

    return {
        "normalized": cleaned,
        "original": original,
        "script_detected": script,
        "language": language,
    }
