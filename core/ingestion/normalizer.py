"""Normalisation textuelle dual-script pour le dialecte algérien.

Gère: Arabizi, arabe, français et texte mixte.
Le but est d'obtenir un texte cohérent, exploitable par l'ABSA et le RAG.
"""

import re
import unicodedata

# ---------------------------------------------------------------------------
# Tables de conversion
# ---------------------------------------------------------------------------

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

_LATIN_TO_ARABIC: dict[str, str] = {
    "a": "ا",
    "b": "ب",
    "c": "ك",
    "d": "د",
    "e": "",
    "f": "ف",
    "g": "ج",
    "h": "ه",
    "i": "ي",
    "j": "ج",
    "k": "ك",
    "l": "ل",
    "m": "م",
    "n": "ن",
    "o": "و",
    "p": "ب",
    "q": "ق",
    "r": "ر",
    "s": "س",
    "t": "ت",
    "u": "و",
    "v": "ف",
    "w": "و",
    "x": "كس",
    "y": "ي",
    "z": "ز",
}

_ARABIZI_LEXICON: dict[str, str] = {
    "7aja": "حاجة",
    "haja": "حاجة",
    "7lib": "حليب",
    "9ar3a": "قارعة",
    "bared": "بارد",
    "bnin": "بنين",
    "bzaf": "بزاف",
    "bzzaf": "بزاف",
    "chwiya": "شوية",
    "ghali": "غالي",
    "khir": "خير",
    "ldid": "لذيذ",
    "m3andhoumch": "ماعندهمش",
    "madha9": "مذاق",
    "mli7": "مليح",
    "mli7a": "مليحة",
    "mliha": "مليحة",
    "nlgah": "نلقاه",
    "rkhis": "رخيص",
    "skhoun": "سخون",
    "ta3m": "طعم",
    "walakin": "ولكن",
    "yla9awh": "يلقاوه",
}

_COMMON_ARABIZI_TOKENS = {
    "7aja",
    "7lib",
    "9ar3a",
    "9al",
    "9oldha",
    "9oldh7a",
    "3andhoum",
    "3olba",
    "bared",
    "bnin",
    "bzaf",
    "bzzaf",
    "ch7al",
    "chwiya",
    "ghali",
    "ghayba",
    "gh7ayba",
    "haja",
    "khir",
    "kh7ir",
    "ldid",
    "ma_kaynch",
    "ma_lgitouch",
    "m3andhoumch",
    "madha9",
    "mli7",
    "mli7a",
    "mliha",
    "nlgah",
    "rkhis",
    "sh3ab",
    "skhoun",
    "ta3m",
    "th3alatha",
    "walakin",
    "yla9awh",
}

_TOKEN_SPLIT = re.compile(r"(\s+)")
_WORD_PARTS = re.compile(r"^([^\w\u0600-\u06FF]*)([\w\u0600-\u06FF]+)([^\w\u0600-\u06FF]*)$")

# Normalisation des graphèmes arabes
_ALEF_VARIANTS = re.compile(r"[أإآ]")
_TA_MARBUTA = re.compile(r"ة")
_YA_ALEF_MAQSURA = re.compile(r"ى")
_TATWEEL = re.compile(r"ـ")
_DIACRITICS = re.compile(r"[\u064B-\u065F\u0670\u06D6-\u06DC\u06DF-\u06E4\u06E7\u06E8\u06EA-\u06ED]")

# Nettoyage général
_URL = re.compile(r"https?://\S+|www\.\S+")
_MENTION = re.compile(r"@\w+")
_HASHTAG = re.compile(r"#\w+")
_MULTI_SPACE = re.compile(r"\s{2,}")
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

# Détection de script
_ARABIC_CHAR = re.compile(r"[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]")
_LATIN_CHAR = re.compile(r"[a-zA-Z\u00C0-\u024F]")
_ARABIZI_DIGITS = re.compile(r"[2395678]")


# ---------------------------------------------------------------------------
# Fonctions internes
# ---------------------------------------------------------------------------

def _count_scripts(text: str) -> tuple[int, int]:
    """Compte les caractères arabes et latins d'un texte."""
    return len(_ARABIC_CHAR.findall(text)), len(_LATIN_CHAR.findall(text))


def _detect_script(text: str) -> str:
    """Détermine le script dominant: arabe, latin ou mixte."""
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


def _clean_noise(text: str) -> str:
    """Supprime URLs, mentions, hashtags, emojis excessifs et espaces parasites."""
    cleaned = _URL.sub("", text)
    cleaned = _MENTION.sub("", cleaned)
    cleaned = _HASHTAG.sub("", cleaned)
    cleaned = _EMOJI.sub(lambda match: match.group(0)[0], cleaned)
    cleaned = _MULTI_SPACE.sub(" ", cleaned)
    return cleaned.strip()


def _clean_for_classifier(text: str) -> str:
    """Nettoie le texte pour le classifieur sans translittérer ni tronquer les emojis.

    Supprime URLs, mentions, hashtags et espaces parasites.
    Garde les emojis complets (signal d'ironie : 😍😍😍🤮).
    Ne fait PAS de translittération Arabizi→Arabe.
    """
    cleaned = _URL.sub("", text)
    cleaned = _MENTION.sub("", cleaned)
    cleaned = _HASHTAG.sub("", cleaned)
    # NE PAS tronquer les emojis — garder le signal complet pour le classifieur
    cleaned = _MULTI_SPACE.sub(" ", cleaned)
    return cleaned.strip()


def _split_token(token: str) -> tuple[str, str, str]:
    """Sépare préfixe ponctuation, coeur de mot et suffixe ponctuation."""
    match = _WORD_PARTS.match(token)
    if not match:
        return token, "", ""
    return match.group(1), match.group(2), match.group(3)


def _is_arabizi_token(token: str) -> bool:
    """Détermine si un token latin ressemble à de l'Arabizi."""
    lowered = token.lower()
    if not lowered:
        return False
    if _ARABIC_CHAR.search(lowered):
        return False
    if _ARABIZI_DIGITS.search(lowered):
        return True
    if lowered in _COMMON_ARABIZI_TOKENS:
        return True
    return False


def _transliterate_arabizi_core(token: str) -> str:
    """Translittère un token Arabizi vers une forme arabe approximative mais cohérente."""
    lowered = token.lower()
    if lowered in _ARABIZI_LEXICON:
        return _ARABIZI_LEXICON[lowered]

    characters: list[str] = []
    index = 0

    while index < len(lowered):
        digram = lowered[index : index + 2]
        if digram in dict(_ARABIZI_DIGRAMS):
            characters.append(dict(_ARABIZI_DIGRAMS)[digram])
            index += 2
            continue

        char = lowered[index]
        if char in _ARABIZI_CHARS:
            characters.append(_ARABIZI_CHARS[char])
        elif char in _LATIN_TO_ARABIC:
            characters.append(_LATIN_TO_ARABIC[char])
        else:
            characters.append(char)
        index += 1

    transliterated = "".join(part for part in characters if part)
    transliterated = re.sub(r"ا{2,}", "ا", transliterated)
    return transliterated


def _convert_arabizi(text: str) -> tuple[str, bool]:
    """Convertit les tokens Arabizi du texte et indique si une conversion a eu lieu."""
    converted_parts: list[str] = []
    converted_any = False

    for part in _TOKEN_SPLIT.split(text):
        if not part or part.isspace():
            converted_parts.append(part)
            continue

        prefix, core, suffix = _split_token(part)
        if not core:
            converted_parts.append(part)
            continue

        if _is_arabizi_token(core):
            converted_core = _transliterate_arabizi_core(core)
            converted_parts.append(f"{prefix}{converted_core}{suffix}")
            converted_any = True
        else:
            converted_parts.append(part)

    return "".join(converted_parts), converted_any


def _normalize_arabic_graphemes(text: str) -> str:
    """Normalise les variantes graphiques arabes."""
    normalized = _ALEF_VARIANTS.sub("ا", text)
    normalized = _TA_MARBUTA.sub("ه", normalized)
    normalized = _YA_ALEF_MAQSURA.sub("ي", normalized)
    normalized = _TATWEEL.sub("", normalized)
    normalized = _DIACRITICS.sub("", normalized)
    return normalized


def _lowercase_latin(text: str) -> str:
    """Met en minuscules uniquement les caractères non arabes."""
    return "".join(
        character.lower()
        if not _ARABIC_CHAR.match(character) and unicodedata.category(character).startswith(("L", "N"))
        else character
        for character in text
    )


def _detect_language(text: str, script: str, arabizi_detected: bool) -> str:
    """Infère la langue dominante parmi darija, français ou mixte."""
    if arabizi_detected:
        return "darija"
    if script == "arabic":
        return "darija"
    if script == "mixed":
        return "mixed"
    return "french"


# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------

def normalize(text: str) -> dict:
    """Normalise un texte en dialecte algérien, arabe, français ou mixte.

    Args:
        text: Texte brut à nettoyer et normaliser.

    Returns:
        Dictionnaire avec le texte normalisé, le texte original,
        le script détecté et la langue inférée.
    """
    original = text

    if not text or not text.strip():
        return {
            "normalized": "",
            "original": original,
            "cleaned_raw": "",  # ← AJOUTER CE CHAMP
            "script_detected": "latin",
            "language": "french",
        }

    cleaned = _clean_noise(text)
    cleaned_for_classifier = _clean_for_classifier(text)  # ← AJOUTER CETTE LIGNE
    script = _detect_script(cleaned)
    converted, arabizi_detected = _convert_arabizi(cleaned)
    normalized = _normalize_arabic_graphemes(converted)
    normalized = _lowercase_latin(normalized)
    normalized = _MULTI_SPACE.sub(" ", normalized).strip()
    language = _detect_language(normalized, _detect_script(normalized), arabizi_detected)

    return {
        "normalized": normalized,
        "original": original,
        "cleaned_raw": cleaned_for_classifier,  # ← AJOUTER CE CHAMP
        "script_detected": script,
        "language": language,
    }
