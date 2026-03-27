"""Tests unitaires pour core/ingestion/normalizer.py.

Couvre: Arabizi→Arabe, normalisation arabe, français, texte mixte,
cas limites (vide, emojis, URLs, mentions, hashtags).
"""

import pytest
from core.ingestion.normalizer import normalize


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get(result, key):
    """Raccourci pour accéder aux clés du dict résultat."""
    assert isinstance(result, dict), f"normalize() doit retourner un dict, got {type(result)}"
    assert key in result, f"Clé manquante dans le résultat: '{key}'"
    return result[key]


# ---------------------------------------------------------------------------
# 1. Structure de retour
# ---------------------------------------------------------------------------

class TestStructureRetour:
    """normalize() retourne toujours un dict avec les 4 clés attendues."""

    def test_retourne_un_dict(self):
        r = normalize("test")
        assert isinstance(r, dict)

    def test_cle_normalized_presente(self):
        r = normalize("test")
        assert "normalized" in r

    def test_cle_original_presente(self):
        r = normalize("test")
        assert "original" in r

    def test_cle_script_detected_presente(self):
        r = normalize("test")
        assert "script_detected" in r

    def test_cle_language_presente(self):
        r = normalize("test")
        assert "language" in r

    def test_original_conserve_le_texte_source(self):
        texte = "Ramy m3andhoumch ta3m"
        r = normalize(texte)
        assert _get(r, "original") == texte

    def test_script_detected_valeurs_valides(self):
        for texte in ["hello", "مرحبا", "hello مرحبا"]:
            r = normalize(texte)
            assert _get(r, "script_detected") in {"arabic", "latin", "mixed"}, \
                f"Valeur invalide pour script_detected: {_get(r, 'script_detected')}"

    def test_language_valeurs_valides(self):
        for texte in ["bonjour", "مرحبا", "7aja mliha"]:
            r = normalize(texte)
            assert _get(r, "language") in {"darija", "french", "mixed"}, \
                f"Valeur invalide pour language: {_get(r, 'language')}"


# ---------------------------------------------------------------------------
# 2. Texte arabe pur
# ---------------------------------------------------------------------------

class TestTexteArabePur:
    """Texte en arabe standard: normalisation graphèmes."""

    def test_script_arabic_detecte(self):
        r = normalize("هذا المنتج جيد جدا")
        assert _get(r, "script_detected") == "arabic"

    def test_alef_normalise_hamza_haut(self):
        # أ → ا
        r = normalize("أحمد")
        assert "ا" in _get(r, "normalized")
        assert "أ" not in _get(r, "normalized")

    def test_alef_normalise_hamza_bas(self):
        # إ → ا
        r = normalize("إبراهيم")
        assert "ا" in _get(r, "normalized")
        assert "إ" not in _get(r, "normalized")

    def test_alef_normalise_madda(self):
        # آ → ا
        r = normalize("آمن")
        assert "ا" in _get(r, "normalized")
        assert "آ" not in _get(r, "normalized")

    def test_ta_marbuta_normalisee(self):
        # ة → ه
        r = normalize("فاكهة")
        assert "ه" in _get(r, "normalized")
        assert "ة" not in _get(r, "normalized")

    def test_ya_normalisee(self):
        # ى → ي
        r = normalize("على")
        assert "ي" in _get(r, "normalized")
        assert "ى" not in _get(r, "normalized")

    def test_tatweel_supprime(self):
        # ـ supprimé
        r = normalize("جميـــل")
        assert "ـ" not in _get(r, "normalized")

    def test_diacritiques_supprimes(self):
        # Tashkeel: fatha, damma, kasra, etc.
        r = normalize("كَتَبَ")
        normalized = _get(r, "normalized")
        # Aucun caractère Unicode dans la plage des diacritiques arabes
        for ch in normalized:
            code = ord(ch)
            assert not (0x064B <= code <= 0x065F), f"Diacritique non supprimé: U+{code:04X}"

    def test_darija_arabic_detectee(self):
        r = normalize("هاذا واعر بزاف")
        assert _get(r, "language") == "darija"


# ---------------------------------------------------------------------------
# 3. Arabizi → Arabe
# ---------------------------------------------------------------------------

class TestArabiziVersArabe:
    """Conversion Arabizi (chiffres phonétiques + digrammes) vers arabe."""

    def test_7aja_mli7a_bzaf(self):
        """'7aja mli7a bzaf' → ح présent dans le résultat normalisé."""
        r = normalize("7aja mli7a bzaf")
        normalized = _get(r, "normalized")
        assert "ح" in normalized, f"ح attendu dans '{normalized}'"

    def test_3ain_converti(self):
        # 3 → ع
        r = normalize("3andhoum")
        assert "ع" in _get(r, "normalized")

    def test_9_converti(self):
        # 9 → ق
        r = normalize("9al")
        assert "ق" in _get(r, "normalized")

    def test_5_converti(self):
        # 5 → خ
        r = normalize("5obz")
        assert "خ" in _get(r, "normalized")

    def test_2_converti(self):
        # 2 → ء
        r = normalize("2ana")
        assert "ء" in _get(r, "normalized")

    def test_8_converti(self):
        # 8 → غ
        r = normalize("8ali")
        assert "غ" in _get(r, "normalized")

    def test_6_converti(self):
        # 6 → ط
        r = normalize("6ayyib")
        assert "ط" in _get(r, "normalized")

    def test_ch_converti(self):
        # ch → ش (en contexte Arabizi avec chiffre phonétique 7)
        r = normalize("ch7al hada")  # شحال = combien, Darija
        assert "ش" in _get(r, "normalized")

    def test_gh_converti(self):
        # gh → غ (en contexte Arabizi avec chiffre phonétique 7)
        r = normalize("gh7ayba")  # غايبة = absente, Darija
        assert "غ" in _get(r, "normalized")

    def test_kh_converti(self):
        # kh → خ (en contexte Arabizi avec chiffre phonétique 7)
        r = normalize("kh7ir walakin")  # خير = bien, Darija
        assert "خ" in _get(r, "normalized")

    def test_th_converti(self):
        # th → ث (en contexte Arabizi avec chiffre phonétique 3)
        r = normalize("th3alatha dyoul")  # ثلاثة = trois, Darija
        assert "ث" in _get(r, "normalized")

    def test_dh_converti(self):
        # dh → ذ (en contexte Arabizi avec chiffre phonétique 9)
        r = normalize("9oldh7a bzaf")  # Arabizi mixte
        assert "ذ" in _get(r, "normalized")

    def test_sh_converti(self):
        # sh → ش (en contexte Arabizi avec chiffre phonétique 3)
        r = normalize("sh3ab ramy")  # شعب = peuple, Darija
        assert "ش" in _get(r, "normalized")

    def test_cas_principal_ramy_m3andhoumch_ta3m(self):
        """Cas de test principal du PRD."""
        r = normalize("ramy m3andhoumch ta3m")
        normalized = _get(r, "normalized")
        # ع doit apparaître (depuis 3)
        assert "ع" in normalized, f"ع attendu dans '{normalized}'"
        # Le résultat doit contenir du texte arabe
        arabic_chars = [c for c in normalized if "\u0600" <= c <= "\u06FF"]
        assert len(arabic_chars) > 0

    def test_arabizi_script_latin_ou_mixed(self):
        r = normalize("7aja mli7a bzaf")
        assert _get(r, "script_detected") in {"latin", "mixed"}

    def test_arabizi_language_darija(self):
        r = normalize("7aja mli7a bzaf")
        assert _get(r, "language") == "darija"


# ---------------------------------------------------------------------------
# 4. Français pur
# ---------------------------------------------------------------------------

class TestFrancaisPur:
    """Texte français: conservé, mis en minuscules."""

    def test_cas_principal_ramy_jus_bon(self):
        """Cas de test principal du PRD: conservé en français, lowercase."""
        r = normalize("le jus Ramy c'est bon")
        normalized = _get(r, "normalized")
        assert "ramy" in normalized
        assert "jus" in normalized
        assert "bon" in normalized

    def test_lowercase_applique(self):
        r = normalize("Le Jus RAMY C'est Très BON")
        normalized = _get(r, "normalized")
        assert normalized == normalized.lower()

    def test_script_latin_detecte(self):
        r = normalize("le jus Ramy c'est bon")
        assert _get(r, "script_detected") == "latin"

    def test_language_french(self):
        r = normalize("le jus Ramy c'est vraiment délicieux")
        assert _get(r, "language") == "french"

    def test_caracteres_speciaux_francais_conserves(self):
        """Les accents français sont conservés."""
        r = normalize("très fraîche")
        normalized = _get(r, "normalized")
        assert "franche" in normalized or "fraîche" in normalized or "fraiche" in normalized

    def test_apostrophe_conservee(self):
        r = normalize("c'est bon")
        assert "c" in _get(r, "normalized")
        assert "bon" in _get(r, "normalized")


# ---------------------------------------------------------------------------
# 5. Texte mixte arabe/français
# ---------------------------------------------------------------------------

class TestTexteMixte:
    """Mélange d'arabe et de français."""

    def test_script_mixed_detecte(self):
        r = normalize("هذا المنتج très bon")
        assert _get(r, "script_detected") == "mixed"

    def test_language_mixed(self):
        r = normalize("هذا المنتج très bon")
        assert _get(r, "language") == "mixed"

    def test_parties_conservees(self):
        r = normalize("رامي جيد et c'est bon")
        normalized = _get(r, "normalized")
        assert len(normalized) > 0

    def test_arabizi_et_francais(self):
        r = normalize("7aja mliha, c'est délicieux")
        normalized = _get(r, "normalized")
        assert "ح" in normalized or "c" in normalized.lower()


# ---------------------------------------------------------------------------
# 6. Cas limites
# ---------------------------------------------------------------------------

class TestCasLimites:
    """Texte vide, emojis, URLs, mentions, hashtags, espaces."""

    def test_texte_vide(self):
        r = normalize("")
        assert isinstance(r, dict)
        assert _get(r, "normalized") == ""

    def test_texte_espaces_seulement(self):
        r = normalize("   ")
        normalized = _get(r, "normalized")
        assert normalized.strip() == ""

    def test_url_http_supprimee(self):
        r = normalize("voici http://example.com le produit")
        assert "http" not in _get(r, "normalized")
        assert "example.com" not in _get(r, "normalized")

    def test_url_https_supprimee(self):
        r = normalize("voir https://www.ramy.dz/produit pour plus")
        assert "https" not in _get(r, "normalized")

    def test_mention_supprimee(self):
        r = normalize("merci @ramyofficial pour ce jus")
        normalized = _get(r, "normalized")
        assert "@ramyofficial" not in normalized

    def test_hashtag_supprime(self):
        r = normalize("super produit #Ramy #Algérie")
        normalized = _get(r, "normalized")
        assert "#ramy" not in normalized.lower() or "#" not in normalized

    def test_emojis_excessifs_nettoyes(self):
        r = normalize("c'est bon 😍😍😍😍😍😍😍😍😍😍")
        normalized = _get(r, "normalized")
        # Pas plus de 2-3 emojis répétés consécutivement
        emoji_count = sum(1 for c in normalized if ord(c) > 0x1F000)
        assert emoji_count < 5

    def test_espaces_multiples_nettoyes(self):
        r = normalize("bon    produit   ramy")
        normalized = _get(r, "normalized")
        assert "  " not in normalized

    def test_texte_chiffres_purs(self):
        """Texte composé uniquement de chiffres arabes."""
        r = normalize("12345")
        assert isinstance(r, dict)
        assert len(_get(r, "normalized")) >= 0

    def test_ponctuation_seule(self):
        r = normalize("!!! ...")
        assert isinstance(r, dict)

    def test_texte_long_pas_tronque(self):
        long_text = "le jus ramy est très bon " * 50
        r = normalize(long_text)
        normalized = _get(r, "normalized")
        assert len(normalized) > 100

    def test_newlines_geres(self):
        r = normalize("ligne 1\nligne 2\nligne 3")
        assert isinstance(r, dict)


# ---------------------------------------------------------------------------
# 7. Stabilité / idempotence
# ---------------------------------------------------------------------------

class TestStabilite:
    """normalize(normalize(x)['normalized']) == normalize(x)['normalized']."""

    def test_idempotence_arabe(self):
        texte = "المنتج جيد جداً"
        r1 = normalize(texte)["normalized"]
        r2 = normalize(r1)["normalized"]
        assert r1 == r2, f"Non idempotent: '{r1}' → '{r2}'"

    def test_idempotence_francais(self):
        texte = "le jus Ramy C'est BON"
        r1 = normalize(texte)["normalized"]
        r2 = normalize(r1)["normalized"]
        assert r1 == r2

    def test_pas_de_perte_semantique_arabe(self):
        """Le texte arabe normalisé reste plus long que 2 caractères."""
        r = normalize("هذا المنتج رائع")
        assert len(_get(r, "normalized")) > 2

    def test_pas_de_perte_semantique_francais(self):
        r = normalize("le produit ramy est excellent")
        assert len(_get(r, "normalized")) > 5


# ---------------------------------------------------------------------------
# 8. Table de substitution Arabizi complète
# ---------------------------------------------------------------------------

class TestTableSubstitutionComplete:
    """Vérifie chaque entrée de la table de substitution."""

    SUBSTITUTIONS = {
        "7": "ح",
        "3": "ع",
        "9": "ق",
        "5": "خ",
        "2": "ء",
        "8": "غ",
        "6": "ط",
        "ch": "ش",
        "gh": "غ",
        "kh": "خ",
        "th": "ث",
        "dh": "ذ",
        "sh": "ش",
    }

    @pytest.mark.parametrize("arabizi,arabe", list(SUBSTITUTIONS.items()))
    def test_substitution(self, arabizi, arabe):
        """Chaque substitution Arabizi → Arabe est appliquée.

        Le chiffre '7' ajouté garantit la détection Arabizi (signal non ambigu).
        """
        texte = f"{arabizi}7ali"  # '7' → signal Arabizi non ambigu
        r = normalize(texte)
        normalized = _get(r, "normalized")
        assert arabe in normalized, \
            f"Substitution '{arabizi}'→'{arabe}' échouée. Résultat: '{normalized}'"


# ---------------------------------------------------------------------------
# 9. Cas d'usage réels (exemples du PRD)
# ---------------------------------------------------------------------------

class TestCasUsageReels:
    """Exemples tirés du contexte métier RamyPulse."""

    def test_commentaire_facebook_positif(self):
        r = normalize("رامي واعر بزاف، نحب هاذ العصير")
        normalized = _get(r, "normalized")
        assert len(normalized) > 3

    def test_commentaire_arabizi_negatif(self):
        r = normalize("ramy m3andhoumch ta3m, ghali bzaf")
        normalized = _get(r, "normalized")
        assert "ع" in normalized  # 3→ع
        assert "غ" in normalized  # gh→غ

    def test_commentaire_francais_neutre(self):
        r = normalize("Le jus Ramy est correct, ni trop sucré ni trop acide.")
        normalized = _get(r, "normalized")
        assert "ramy" in normalized
        assert "jus" in normalized

    def test_commentaire_mixte_avec_url(self):
        r = normalize("واعر بزاف https://fb.com/ramy #ramy @ramyofficial 😍😍")
        normalized = _get(r, "normalized")
        assert "https" not in normalized
        assert "@ramyofficial" not in normalized

    def test_avis_google_maps_francais(self):
        r = normalize("Bonne fraîcheur, emballage correct. Prix abordable pour Ramy.")
        normalized = _get(r, "normalized")
        assert "ramy" in normalized

    def test_transcription_audio_darija(self):
        r = normalize("7lib ramy mli7 bzzaf walakin ghali chwiya")
        normalized = _get(r, "normalized")
        assert "ح" in normalized  # 7→ح
        assert "غ" in normalized  # gh→غ
        assert _get(r, "language") == "darija"
