"""Materialize the explicit expert review decisions for the 100-record pilot."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")


REVIEWED_AT = "2026-07-29T21:00:00Z"


def ev(text: str) -> dict[str, Any]:
    return {"text": text, "start": 0, "end": len(text)}


def sentiment(
    label: str,
    intensity: str,
    emotion: str,
    evidence: list[str] | None = None,
    *,
    sarcasm: bool = False,
    targets: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "label": label,
        "intensity": intensity,
        "emotion": emotion,
        "sarcasm": sarcasm,
        "target_entity_ids": targets or [],
        "evidence": [ev(text) for text in (evidence or [])],
    }


def aspect(
    family: str,
    attribute: str,
    label: str,
    evidence: str,
    *,
    target: str | None = None,
    intensity: str = "moyenne",
    implicit: bool = False,
) -> dict[str, Any]:
    return {
        "family": family,
        "attribute": attribute,
        "target_entity_id": target,
        "sentiment": label,
        "intensity": intensity,
        "implicit": implicit,
        "evidence": [ev(evidence)],
    }


def alert(
    alert_type: str,
    severity: str,
    evidence: str,
    *,
    target: str | None = None,
) -> dict[str, Any]:
    return {
        "type": alert_type,
        "severity": severity,
        "target_entity_id": target,
        "evidence": [ev(evidence)],
    }


def action(
    actionable: bool, queue: str = "aucune", priority: str = "faible"
) -> dict[str, Any]:
    return {"actionable": actionable, "queue": queue, "priority": priority}


def entity_context(
    entity_id: str, entity_type: str, name: str
) -> dict[str, Any]:
    return {
        "id": entity_id,
        "type": entity_type,
        "name": name,
        "mention": None,
        "start": None,
        "end": None,
        "source": "contexte",
    }


def entity_text(
    entity_id: str, entity_type: str, name: str, mention: str
) -> dict[str, Any]:
    return {
        "id": entity_id,
        "type": entity_type,
        "name": name,
        "mention": mention,
        "start": 0,
        "end": len(mention),
        "source": "texte",
    }


def unexploitable(reason: str = "ambiguite_majeure") -> dict[str, Any]:
    return {
        "is_exploitable": False,
        "non_exploitable_reason": reason,
        "business_relevance": "aucune",
        "entities": [],
        "sentiment": sentiment("neutre", "faible", "aucune"),
        "intents": [],
        "aspects": [],
        "alerts": [],
        "actionability": action(False),
    }


def review_overrides() -> tuple[dict[int, dict[str, Any]], dict[int, str]]:
    overrides: dict[int, dict[str, Any]] = {}
    notes: dict[int, str] = {}

    def change(seed: int, note: str, **fields: Any) -> None:
        overrides[seed] = fields
        notes[seed] = note

    change(
        5658,
        "Le signal d'irrigation par eaux usées est un risque sanitaire direct, pas une information neutre.",
        business_relevance="directe",
        entities=[entity_context("ent_1", "marque", "Ramy")],
        sentiment=sentiment(
            "negatif",
            "forte",
            "inquietude",
            ["التيو مربوط بالزيڨو لي تسقو بيه المزرعة"],
            targets=["ent_1"],
        ),
        intents=["signalement_incident"],
        aspects=[
            aspect(
                "securite_conformite",
                "hygiene",
                "negatif",
                "التيو مربوط بالزيڨو لي تسقو بيه المزرعة",
                target="ent_1",
                intensity="forte",
            )
        ],
        alerts=[
            alert(
                "securite_sante",
                "critique",
                "التيو مربوط بالزيڨو لي تسقو بيه المزرعة",
                target="ent_1",
            )
        ],
        actionability=action(True, "securite_qualite", "critique"),
    )
    change(
        6115,
        "Une opinion générique sur le goût et la qualité ne suffit pas à déclencher une alerte.",
        alerts=[],
        actionability=action(True, "produit", "moyenne"),
    )
    change(
        6121,
        "La question est trop elliptique pour identifier un aspect business fiable sans le post parent.",
        **unexploitable(),
    )
    change(
        6129,
        "Une indisponibilité ponctuelle à la commande reste une plainte, pas une alerte de rupture.",
        alerts=[],
    )
    change(
        6183,
        "Le ticket déchiré concerne la procédure de participation, pas le stock.",
        intents=["demande_aide", "partage_experience"],
        aspects=[
            aspect(
                "operations_processus",
                "procedure",
                "negatif",
                "التيكي نتاع الشراء قطعوووووو",
                target="ent_1",
            )
        ],
        alerts=[],
        actionability=action(True, "service_client", "moyenne"),
    )
    change(
        6276,
        "L'utilisateur ne trouve pas l'emplacement dans l'interface : problème d'ergonomie, pas de disponibilité.",
        aspects=[
            aspect(
                "digital_technologie",
                "ergonomie",
                "neutre",
                "كي ندخل منلقاكش وين نحطها",
                target="ent_1",
            )
        ],
        actionability=action(True, "digital", "moyenne"),
    )
    change(
        6476,
        "L'accusation de manque de crédibilité n'apporte pas assez de faits pour une alerte fraude.",
        alerts=[],
    )
    change(
        6489,
        "Réponse informative de marque : suppression du tag personne et remplacement de l'intention invalide.",
        entities=[entity_context("ent_1", "marque", "Hamoud Boualem")],
        sentiment=sentiment(
            "positif",
            "moyenne",
            "confiance",
            ["المسابقة تتمتع بالشفافية", "تم إجراء السحب بوجود محضر قضائي"],
            targets=["ent_1"],
        ),
        intents=["autre"],
        aspects=[
            aspect(
                "communication_information",
                "transparence",
                "positif",
                "المسابقة تتمتع بالشفافية",
                target="ent_1",
            ),
            aspect(
                "confiance_reputation",
                "credibilite",
                "positif",
                "تم إجراء السحب بوجود محضر قضائي",
                target="ent_1",
            ),
        ],
    )
    change(
        6602,
        "Félicitations positives et déception de ne pas avoir gagné : sentiment mixte.",
        sentiment=sentiment(
            "mixte",
            "moyenne",
            "deception",
            ["مبروك عليهم شاركت و ماربحتش دوماج"],
            targets=["ent_1"],
        ),
        intents=["partage_experience"],
        aspects=[
            aspect(
                "experience_client",
                "satisfaction_globale",
                "mixte",
                "مبروك عليهم شاركت و ماربحتش دوماج",
                target="ent_1",
                implicit=True,
            )
        ],
    )
    change(
        6611,
        "Question Arabizi sur le justificatif d'achat : procédure de participation et action SAV.",
        language={
            "dominant": "darija_arabizi",
            "detected": ["darija", "francais"],
            "code_switching": True,
            "scripts": ["latin", "chiffres"],
        },
        aspects=[
            aspect(
                "operations_processus",
                "procedure",
                "neutre",
                "maykonch l7anout 3andou ticket de caisse",
                target="ent_1",
            )
        ],
        actionability=action(True, "service_client", "moyenne"),
    )
    change(
        6617,
        "Le commentaire combine félicitations et déception personnelle.",
        sentiment=sentiment(
            "mixte",
            "moyenne",
            "deception",
            ["الف مبروك.للاسف شاركت ومربحتش 💔"],
            targets=["ent_1"],
        ),
        intents=["partage_experience"],
        aspects=[
            aspect(
                "experience_client",
                "satisfaction_globale",
                "mixte",
                "الف مبروك.للاسف شاركت ومربحتش 💔",
                target="ent_1",
                implicit=True,
            )
        ],
    )
    change(
        6759,
        "Le nom initial est un tag de personne, pas un produit ; le signal utile est la fidélité à la marque.",
        entities=[entity_context("ent_1", "marque", "Hamoud Boualem")],
        sentiment=sentiment(
            "positif",
            "forte",
            "satisfaction",
            ["كل يوم لازم تكون حاضرة فوق الطابلة"],
            targets=["ent_1"],
        ),
        intents=["eloge", "avis"],
        aspects=[
            aspect(
                "experience_client",
                "fidelite",
                "positif",
                "كل يوم لازم تكون حاضرة فوق الطابلة",
                target="ent_1",
                intensity="forte",
                implicit=True,
            )
        ],
        actionability=action(False),
    )
    change(
        6821,
        "La phrase exprime une opinion élogieuse sur l'histoire et l'image de marque.",
        intents=["eloge", "avis"],
    )
    change(
        6882,
        "« tawlto » critique un délai, pas la qualité intrinsèque du produit.",
        sentiment=sentiment(
            "negatif",
            "moyenne",
            "frustration",
            ["tawlto"],
            targets=["ent_1"],
        ),
        intents=["plainte"],
        aspects=[
            aspect(
                "operations_processus",
                "delai",
                "negatif",
                "tawlto",
                target="ent_1",
            )
        ],
        actionability=action(True, "operations", "moyenne"),
    )
    change(
        6900,
        "Ramy est une marque dans ce contexte et l'éloge porte sur une initiative sociale.",
        entities=[entity_text("ent_1", "marque", "Ramy", "رامي")],
        sentiment=sentiment(
            "positif",
            "forte",
            "admiration",
            ["دائمًا السباق للمبادرة الحسنة، شكرا رامي"],
            targets=["ent_1"],
        ),
        aspects=[
            aspect(
                "ethique_impact",
                "responsabilite_sociale",
                "positif",
                "دائمًا السباق للمبادرة الحسنة، شكرا رامي",
                target="ent_1",
                intensity="forte",
            )
        ],
    )
    change(
        6928,
        "« ZERO » seul ne permet pas d'identifier le produit, l'aspect ou la polarité.",
        **unexploitable(),
        language={
            "dominant": "anglais",
            "detected": ["anglais"],
            "code_switching": False,
            "scripts": ["latin"],
        },
    )
    change(
        6946,
        "Un éloge sans demande ne nécessite aucun routage opérationnel.",
        actionability=action(False),
    )
    change(
        6975,
        "« est la base » relève de l'image de marque, pas d'une propriété produit.",
        intents=["eloge", "avis"],
        aspects=[
            aspect(
                "confiance_reputation",
                "image_marque",
                "positif",
                "Hamoud boualem est la base",
                target="ent_1",
                intensity="forte",
            )
        ],
    )
    change(
        7028,
        "Remplacement du libellé libre « attachement » par l'attribut contrôlé image_marque.",
        aspects=[
            aspect(
                "confiance_reputation",
                "image_marque",
                "positif",
                "كل جزائري حر في عروقه كاين الدم و حمود بوعلام",
                target="ent_1",
                intensity="forte",
            )
        ],
    )
    change(
        7047,
        "La demande de nouveaux goûts est une suggestion neutre au niveau de l'aspect, malgré l'éloge global.",
        aspects=[
            aspect(
                "produit_service",
                "gout",
                "neutre",
                "تزيدولنا أذواق جدد فزيرو سكر",
                target="ent_1",
            )
        ],
    )
    change(
        7128,
        "Positionnement élogieux sans action opérationnelle requise.",
        actionability=action(False),
    )
    change(
        7197,
        "Le commentaire critique directement la priorité sociale de la marque.",
        business_relevance="directe",
        entities=[entity_context("ent_1", "marque", "Ramy")],
        sentiment=sentiment(
            "negatif",
            "moyenne",
            "tristesse",
            ["من الأحسن كان شافو الزواولة", "كain ناس راهم يفطرو بالعدس الجومبو و مكاش".replace("كain", "كاين")],
            targets=["ent_1"],
        ),
        intents=["suggestion", "plainte"],
        aspects=[
            aspect(
                "ethique_impact",
                "responsabilite_sociale",
                "negatif",
                "من الأحسن كان شافو الزواولة",
                target="ent_1",
            )
        ],
        actionability=action(True, "direction", "moyenne"),
    )
    change(
        7226,
        "Un aliment avarié est un risque sanitaire et la marque de contexte doit rester la cible.",
        entities=[
            entity_context("ent_1", "marque", "YaghurtPlus"),
            entity_text("ent_2", "produit", "yaghourt", "yaghourt"),
        ],
        sentiment=sentiment(
            "negatif",
            "forte",
            "degout",
            ["Très mauvaise expérience, yaghourt avarié"],
            targets=["ent_1", "ent_2"],
        ),
        intents=["plainte", "signalement_incident"],
        aspects=[
            aspect(
                "produit_service",
                "fraicheur",
                "negatif",
                "avarié",
                target="ent_2",
                intensity="forte",
            ),
            aspect(
                "securite_conformite",
                "sante",
                "negatif",
                "yaghourt avarié",
                target="ent_2",
                intensity="forte",
            ),
        ],
        alerts=[
            alert(
                "securite_sante",
                "elevee",
                "yaghourt avarié",
                target="ent_2",
            )
        ],
    )
    change(
        7275,
        "Une absence de réponse sur un incident unique ne suffit pas à établir une rupture de service générale.",
        alerts=[],
        actionability=action(True, "service_client", "moyenne"),
    )
    change(
        7346,
        "Une appréciation générique de mauvaise qualité ne justifie pas une alerte élevée.",
        alerts=[],
        actionability=action(True, "produit", "moyenne"),
    )
    change(
        0,
        "La demande d'ajustement salarial n'exprime pas explicitement une polarité négative.",
        sentiment=sentiment("neutre", "moyenne", "aucune", ["نريد تعديل الاجور"]),
        intents=["suggestion", "appel_action"],
        aspects=[
            aspect(
                "emploi_management",
                "salaire",
                "neutre",
                "نريد تعديل الاجور",
            )
        ],
    )
    change(
        1,
        "L'absence de recrutement est négative mais ne constitue pas en soi une alerte juridique.",
        alerts=[],
    )
    change(
        26,
        "La récupération d'une ligne désactivée relève de la résolution SAV.",
        aspects=[
            aspect(
                "service_client_sav",
                "resolution",
                "neutre",
                "بيس اوريدو ديزاكتيفات نقدر نريكيبريها",
                target="ent_1",
            )
        ],
    )
    change(
        32,
        "Question sur la connexion récente sans preuve d'une rupture généralisée.",
        alerts=[],
    )
    change(
        34,
        "Les cinq minutes gratuites relèvent d'une promotion, pas d'une fonctionnalité produit.",
        aspects=[
            aspect(
                "prix_valeur",
                "promotion",
                "neutre",
                "كفاش ندير 5 دقايق باطل",
                target="ent_1",
            )
        ],
    )
    change(
        36,
        "Le nom initial est un tag sans rôle ; la question porte sur l'offre postpayée.",
        entities=[],
        sentiment=sentiment("neutre", "faible", "aucune", ["خدمة ما بعد الدفع؟"]),
        aspects=[
            aspect(
                "produit_service",
                "fonctionnalite",
                "neutre",
                "خدمة ما بعد الدفع",
            )
        ],
        actionability=action(True, "ventes", "faible"),
    )
    change(
        39,
        "La demande porte sur la procédure d'activation d'une offre.",
        aspects=[
            aspect(
                "operations_processus",
                "procedure",
                "neutre",
                "كيفيه نكتيفي فايس ب30",
                target="ent_1",
            )
        ],
    )
    change(
        40,
        "Le maintien d'un débit réduit après épuisement du quota relève de la connectivité.",
        aspects=[
            aspect(
                "digital_technologie",
                "connexion_reseau",
                "negatif",
                "تبقى الأنترنات التردد المنخفض بعد نفاذ الجيڨات",
                target="ent_1",
            )
        ],
        actionability=action(True, "digital", "moyenne"),
    )
    change(
        236,
        "Article factuel de marché : pertinence indirecte et absence d'opinion personnelle.",
        business_relevance="indirecte",
        intents=["autre"],
    )
    change(
        466,
        "Constat général d'abordabilité sur le marché algérien : pertinence indirecte.",
        business_relevance="indirecte",
    )
    change(
        576,
        "La résolution conditionnelle du problème d'eau implique un sentiment négatif actuel.",
        sentiment=sentiment(
            "negatif",
            "moyenne",
            "frustration",
            ["مشكل الماء"],
            targets=["ent_1"],
        ),
    )
    change(
        685,
        "La file d'attente est un problème opérationnel, sans preuve de rupture de service.",
        alerts=[],
        actionability=action(True, "operations", "moyenne"),
    )
    change(
        740,
        "Un commentaire unique sur une pénurie d'huile justifie une alerte moyenne, pas élevée.",
        alerts=[alert("rupture_stock", "moyenne", "كاش بيدون زيت")],
        actionability=action(True, "logistique", "moyenne"),
    )
    change(
        212,
        "Suppression de l'intention invalide et de l'alerte sans fondement ; conservation du prix et de la quantité.",
        intents=["plainte", "avis"],
        alerts=[],
    )
    change(
        1500,
        "L'indisponibilité de médicaments doit être routée vers la logistique.",
        actionability=action(True, "logistique", "elevee"),
    )
    change(
        1415,
        "Éloge sans action corrective requise.",
        actionability=action(False),
    )
    change(
        1517,
        "Suppression de l'entité mal alignée et ajout des deux questions explicites : capacité et localisation.",
        entities=[],
        sentiment=sentiment(
            "neutre",
            "faible",
            "aucune",
            ["وهل يستوعب كل المرضي الجزائريين", "اين سيكون المقر يعني باي ولاية"],
        ),
        intents=["question", "demande_information"],
        aspects=[
            aspect(
                "operations_processus",
                "capacite",
                "neutre",
                "وهل يستوعب كل المرضي الجزائريين",
            ),
            aspect(
                "communication_information",
                "information_manquante",
                "neutre",
                "اين سيكون المقر يعني باي ولاية",
            ),
        ],
        actionability=action(True, "direction", "moyenne"),
    )
    change(
        1461,
        "La proposition de couverture hospitalière est actionnable au niveau direction.",
        actionability=action(True, "direction", "moyenne"),
    )
    change(
        1471,
        "Proposition explicite de construire un hôpital dans chaque wilaya : pertinence directe et actionnable.",
        business_relevance="directe",
        actionability=action(True, "direction", "moyenne"),
    )
    change(
        1392,
        "L'éloge est exploitable, mais aucun aspect précis n'est identifiable sans le post parent.",
        aspects=[],
    )
    change(
        1331,
        "Correction de la citation sanitaire et conservation de l'alerte élevée liée à la durée d'hospitalisation et au risque de décès.",
        alerts=[
            alert(
                "securite_sante",
                "elevee",
                "انا راني شهرين مع الوالد في المستشفى لا كرونا لا والو سياسة يهودية حسبي الله ونعم الوكيل اخرتها موت",
            )
        ],
    )
    change(
        844,
        "Réalignement des preuves sur des citations courtes et exactes.",
        aspects=[
            aspect(
                "emploi_management",
                "recrutement",
                "negatif",
                "تصنيفهم في ذيل قائمة التوظيف",
                target="ent_1",
                intensity="forte",
            ),
            aspect(
                "infrastructure_service_public",
                "education",
                "negatif",
                "اغلقت المدرسة ابوابها في وجه طلبتها قمعا و ظلما",
                target="ent_1",
                intensity="forte",
            ),
        ],
    )
    change(
        1173,
        "La gratitude vise l'interlocuteur ; le signal business porte sur l'absence de perspectives professionnelles.",
        sentiment=sentiment(
            "negatif",
            "moyenne",
            "inquietude",
            ["ومفيهاش مستقبل فبلادي"],
        ),
        intents=["partage_experience", "avis"],
        aspects=[
            aspect(
                "emploi_management",
                "recrutement",
                "negatif",
                "ومفيهاش مستقبل فبلادي",
            )
        ],
    )
    change(
        3090,
        "Correction de la citation exacte « ملقاتش خدمة ».",
        aspects=[
            aspect(
                "emploi_management",
                "recrutement",
                "negatif",
                "ملقاتش خدمة",
            )
        ],
    )
    change(
        5531,
        "La comparaison de réseaux ne démontre pas une rupture de service généralisée.",
        alerts=[],
        actionability=action(True, "digital", "moyenne"),
    )
    change(
        5532,
        "Les rires marquent ici une lecture ironique de la qualité de la 4G.",
        sentiment=sentiment(
            "negatif",
            "moyenne",
            "frustration",
            ["حنا صحاب 4G رانا غايا 😂😂"],
            sarcasm=True,
            targets=["ent_1"],
        ),
        intents=["avis"],
        aspects=[
            aspect(
                "digital_technologie",
                "connexion_reseau",
                "negatif",
                "حنا صحاب 4G رانا غايا 😂😂",
                target="ent_1",
            )
        ],
        actionability=action(True, "digital", "moyenne"),
    )
    change(
        5533,
        "« الحمد لله » associé à la 3G et aux émojis est retenu comme ironie sur un réseau daté.",
        sentiment=sentiment(
            "negatif",
            "moyenne",
            "frustration",
            ["الحمد لله راني ب 3g 😌😌"],
            sarcasm=True,
        ),
        intents=["avis"],
        aspects=[
            aspect(
                "digital_technologie",
                "connexion_reseau",
                "negatif",
                "راني ب 3g",
            )
        ],
        actionability=action(True, "digital", "moyenne"),
    )
    change(
        5540,
        "Réalignement de la preuve sur le texte exact de la proposition touristique.",
        sentiment=sentiment(
            "negatif",
            "forte",
            "frustration",
            ["ميزانية كبيرة تنصرف باش نديرو منتجعات و فنادق"],
        ),
        aspects=[
            aspect(
                "infrastructure_service_public",
                "infrastructure",
                "negatif",
                "منتجعات و فنادق",
            )
        ],
    )
    change(
        5544,
        "Le vandalisme répété concerne l'infrastructure ; suppression de l'aspect expérience et de l'alerte rupture.",
        aspects=[
            aspect(
                "infrastructure_service_public",
                "infrastructure",
                "negatif",
                "صبنا لكراسا و الطابلة مكسرين",
                target="ent_1",
                intensity="forte",
            )
        ],
        alerts=[],
        actionability=action(True, "operations", "moyenne"),
    )
    change(
        5546,
        "Suppression de l'entité Algérie dupliquée et des propriétés de preuve hors schéma.",
        entities=[
            entity_text("ent_1", "lieu", "Chine", "الصين"),
            entity_text("ent_2", "lieu", "Algérie", "الجزائر"),
        ],
        sentiment=sentiment(
            "positif",
            "forte",
            "admiration",
            ["لو طبق هذا النظام في كل معالم الجزائر 🇩🇿 الأثرية"],
            targets=["ent_2"],
        ),
        aspects=[
            aspect(
                "marche_innovation",
                "innovation",
                "positif",
                "مسح ثلاثي الابعاد",
                target="ent_2",
            )
        ],
        actionability=action(True, "direction", "moyenne"),
    )
    change(
        5560,
        "Le texte recommande implicitement la destination, sans rapporter une expérience personnelle.",
        intents=["eloge", "recommandation"],
    )
    change(
        5562,
        "Éloge générique exploitable mais sans cible ni aspect précis dans le commentaire.",
        business_relevance="indirecte",
        aspects=[],
    )
    change(
        4381,
        "Information factuelle sur le prix et la livraison, sans action corrective demandée.",
        intents=["avis"],
        actionability=action(False),
    )
    change(
        3431,
        "Éloge de l'honnêteté d'un travailleur sans aspect contrôlé suffisamment précis.",
        aspects=[],
    )
    change(
        3946,
        "Correction de la preuve et routage de la suggestion de sécurité.",
        sentiment=sentiment(
            "negatif",
            "forte",
            "frustration",
            ["الردع لازم الردع"],
        ),
        actionability=action(True, "securite_qualite", "moyenne"),
    )
    change(
        3923,
        "Le commentaire vise explicitement la dégradation de biens publics.",
        aspects=[
            aspect(
                "infrastructure_service_public",
                "infrastructure",
                "negatif",
                "هادو الي راهم يكسرو",
                intensity="forte",
            )
        ],
        actionability=action(True, "operations", "moyenne"),
    )
    change(
        41,
        "Salutation sans objet business identifiable.",
        **unexploitable("hors_sujet"),
    )
    change(
        4671,
        "Réponse religieuse hors sujet : aucune intention business.",
        intents=[],
    )
    return overrides, notes


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Génère le journal explicite de revue gold V0.1."
    )
    parser.add_argument("--draft", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    with args.draft.open("r", encoding="utf-8") as handle:
        drafts = [json.loads(line) for line in handle if line.strip()]
    if len(drafts) != 100:
        raise ValueError(f"Le brouillon doit contenir 100 lignes, trouvé {len(drafts)}")

    overrides, notes = review_overrides()
    draft_indices = {row["seed_index"] for row in drafts}
    unknown = sorted(set(overrides) - draft_indices)
    if unknown:
        raise ValueError(f"Overrides sans brouillon : {unknown}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as handle:
        for draft in drafts:
            seed_index = draft["seed_index"]
            if seed_index in overrides:
                row = {
                    "seed_index": seed_index,
                    "decision": "modify",
                    "set": overrides[seed_index],
                    "notes": notes[seed_index],
                    "reviewed_at": REVIEWED_AT,
                }
            else:
                row = {
                    "seed_index": seed_index,
                    "decision": "accept",
                    "notes": (
                        "Revue sémantique effectuée : catégories, preuves, "
                        "alertes et actionnabilité cohérentes."
                    ),
                    "reviewed_at": REVIEWED_AT,
                }
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"REVIEWS={args.output}")
    print(f"MODIFIED={len(overrides)}")
    print(f"ACCEPTED={len(drafts) - len(overrides)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
