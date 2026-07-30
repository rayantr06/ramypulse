# RamyPulse SLM V2 — Guide d'annotation business V0.1

## 1. Objet

Ce document définit le contrat d'annotation d'un SLM multilingue destiné à analyser des commentaires business de secteurs variés : produits de grande consommation, télécommunications, banque, commerce, services, transport, tourisme, santé, éducation, services publics et plateformes numériques.

La V0.1 est une base de travail contrôlée. Elle doit être testée sur les Lots 1, 2 et 3, puis consolidée avant de devenir la V1 du contrat de production.

## 2. Ce que montre le Lot 1

Le Lot 1 récupéré contient 3 000 commentaires et couvre les indices 0 à 2 999 de `master_seed_7k.jsonl`.

Constats principaux :

- 2 999 sorties JSON récupérables sur 3 000 ;
- 4 655 annotations d'aspect ;
- 3 024 libellés d'aspect de surface ;
- 2 784 libellés après normalisation orthographique ;
- 2 277 libellés normalisés présents une seule fois ;
- 96,5 % des preuves d'aspect sont retrouvées dans le texte source ;
- langues dominantes : 1 539 arabe MSA, 1 392 Darija arabe, 53 mixtes et 15 Arabizi ;
- source : 100 % `massinissa_algerian_corpus` ;
- principaux thèmes : économie, santé, social, éducation, religion et médias.

Conclusion : le Lot 1 est suffisamment riche pour découvrir les dimensions sémantiques principales, mais ses milliers de libellés libres ne doivent pas être utilisés directement comme classes d'entraînement. Il est également trop homogène en source et en écriture arabe pour figer seul l'ontologie finale.

## 3. Principes du contrat

1. Les valeurs catégorielles sont fermées et versionnées.
2. Une preuve est toujours une citation exacte du commentaire avec ses offsets.
3. Une marque ou un produit n'est jamais inventé.
4. Une entité connue grâce au contexte est distinguée d'une entité écrite dans le texte.
5. Les aspects sont hiérarchiques : une famille stable et un attribut contrôlé.
6. Le sentiment global ne remplace pas le sentiment par aspect.
7. `mixte` exige au moins un signal positif et un signal négatif réels.
8. Un commentaire non exploitable produit des tableaux `aspects` et `alerts` vides.
9. Les alertes sont réservées aux risques opérationnels ou réputationnels réels.
10. La confiance n'est pas demandée au modèle sous forme d'auto-évaluation libre.

## 4. Schéma fonctionnel

### 4.1 Exploitabilité

`is_exploitable` indique si le commentaire contient assez d'information pour produire au moins une annotation fiable.

Si la valeur est `false`, `non_exploitable_reason` doit prendre une valeur parmi :

- `hors_sujet`
- `spam`
- `texte_insuffisant`
- `incomprehensible`
- `langue_non_supportee`
- `bruit_technique`
- `ambiguite_majeure`

Un commentaire court peut rester exploitable. Par exemple, « روعة » est exploitable comme éloge positif si le contexte identifie clairement l'objet évalué.

### 4.2 Pertinence business

- `directe` : le commentaire évalue, questionne ou signale un produit, un service, une organisation, une expérience, une politique ou un processus.
- `indirecte` : le commentaire apporte un contexte de marché, de réputation, d'emploi ou de comportement utile à la veille.
- `aucune` : aucun signal business exploitable.

### 4.3 Langues

La langue dominante est une valeur unique :

- `darija_arabe`
- `darija_arabizi`
- `arabe_msa`
- `francais`
- `anglais`
- `tamazight_latin`
- `tamazight_tifinagh`
- `mixte`
- `autre`

`detected` conserve toutes les langues réellement présentes. `scripts` décrit les écritures utilisées. `code_switching` vaut `true` seulement lorsqu'il existe une alternance linguistique réelle, pas pour un simple nom de marque étranger.

### 4.4 Entités

Types autorisés :

- `marque`
- `organisation`
- `produit`
- `service`
- `personne`
- `lieu`
- `concurrent`
- `campagne`
- `politique_publique`
- `autre`

Pour une entité présente dans le commentaire, `mention`, `start` et `end` sont obligatoires et `source` vaut `texte`.

Pour une entité connue grâce au contexte de collecte, les trois champs sont `null` et `source` vaut `contexte`.

### 4.5 Sentiment

Le label global est :

- `negatif`
- `neutre`
- `positif`
- `mixte`

L'intensité est séparée :

- `faible`
- `moyenne`
- `forte`

Cette séparation évite de multiplier artificiellement les classes avec `tres_positif` et `tres_negatif`, tout en conservant l'intensité nécessaire aux alertes et aux indicateurs.

Émotions principales :

- satisfaction, admiration, joie, confiance ;
- déception, frustration, colère, inquiétude, peur, tristesse, dégoût ;
- surprise, aucune ou autre.

Le sarcasme est un booléen indépendant.

### 4.6 Intentions

Un commentaire peut recevoir jusqu'à trois intentions :

- `avis`
- `plainte`
- `eloge`
- `question`
- `demande_information`
- `demande_aide`
- `suggestion`
- `recommandation`
- `comparaison`
- `intention_achat`
- `partage_experience`
- `signalement_incident`
- `appel_action`
- `promotion_spam`
- `tag_mention`
- `autre`

`plainte` exprime une insatisfaction. `signalement_incident` rapporte un problème concret et vérifiable. Les deux peuvent coexister.

## 5. Ontologie des aspects

### 5.1 `produit_service`

Qualité et propriétés intrinsèques :

- `qualite_generale`
- `performance`
- `fiabilite`
- `durabilite`
- `fonctionnalite`
- `design`
- `gout`
- `odeur`
- `texture`
- `fraicheur`
- `emballage`
- `quantite`
- `hygiene`
- `securite_produit`
- `conformite_description`

### 5.2 `prix_valeur`

- `prix`
- `abordabilite`
- `rapport_qualite_prix`
- `promotion`
- `transparence_prix`
- `facturation`

### 5.3 `disponibilite_acces`

- `stock`
- `rupture`
- `couverture_geographique`
- `accessibilite`
- `horaires`
- `canal_achat`

### 5.4 `experience_client`

- `satisfaction_globale`
- `facilite`
- `attente`
- `accueil`
- `comportement_personnel`
- `personnalisation`
- `fidelite`

### 5.5 `service_client_sav`

- `reactivite`
- `resolution`
- `remboursement`
- `garantie`
- `traitement_reclamation`
- `professionnalisme`

### 5.6 `livraison_logistique`

- `delai_livraison`
- `etat_reception`
- `suivi_commande`
- `distribution`
- `approvisionnement`

### 5.7 `digital_technologie`

- `application`
- `site_web`
- `ergonomie`
- `bug`
- `connexion_reseau`
- `paiement`
- `securite_donnees`

### 5.8 `communication_information`

- `clarte`
- `exactitude`
- `transparence`
- `publicite`
- `promesse`
- `information_manquante`

### 5.9 `confiance_reputation`

- `confiance`
- `credibilite`
- `image_marque`
- `authenticite`
- `recommandation`
- `comparaison_concurrent`

### 5.10 `operations_processus`

- `efficacite`
- `delai`
- `procedure`
- `coherence`
- `continuite_service`
- `capacite`

### 5.11 `emploi_management`

- `recrutement`
- `salaire`
- `conditions_travail`
- `management`
- `formation`
- `equite_interne`

### 5.12 `securite_conformite`

- `securite`
- `sante`
- `hygiene`
- `conformite_legale`
- `fraude`
- `confidentialite`

### 5.13 `ethique_impact`

- `equite`
- `discrimination`
- `corruption`
- `responsabilite_sociale`
- `environnement`
- `impact_local`

### 5.14 `marche_innovation`

- `innovation`
- `positionnement`
- `concurrence`
- `production_locale`
- `import_export`
- `tendance`

### 5.15 `infrastructure_service_public`

- `infrastructure`
- `transport`
- `eau_energie`
- `sante_publique`
- `education`
- `administration`
- `couverture_territoriale`

## 6. Règles d'annotation des aspects

Chaque aspect contient :

- une `family` ;
- un `attribute` autorisé pour cette famille ;
- une cible éventuelle ;
- un sentiment ;
- une intensité ;
- un indicateur `implicit` ;
- une à trois preuves exactes.

Règles :

1. Ne jamais produire `aucun_aspect`, `general`, `autre_aspect` ou une nouvelle chaîne libre.
2. S'il n'existe aucun aspect fiable, retourner `aspects: []`.
3. Choisir la catégorie la plus spécifique supportée par la preuve.
4. Limiter l'annotation aux huit aspects les plus utiles.
5. Un aspect implicite doit rester justifiable par une preuve textuelle.
6. Si deux interprétations sont également plausibles, ne pas annoter l'aspect et router l'exemple vers la revue.

## 7. Alertes

Types autorisés :

- `qualite_produit`
- `securite_sante`
- `fraude_arnaque`
- `juridique_conformite`
- `rupture_service`
- `rupture_stock`
- `reputation_virale`
- `donnees_confidentialite`
- `harcelement_discrimination`

Sévérité :

- `faible` : signal isolé, impact limité ;
- `moyenne` : incident concret nécessitant un suivi ;
- `elevee` : risque important, répétition ou impact sur plusieurs clients ;
- `critique` : danger immédiat, fraude grave, incident sanitaire ou interruption majeure.

Une simple opinion négative n'est pas une alerte.

## 8. Actionnabilité

Le routage possible est :

- produit
- pricing
- service client
- ventes
- opérations
- logistique
- digital
- communication
- ressources humaines
- juridique/conformité
- sécurité/qualité
- direction
- aucune

L'actionnabilité transforme l'annotation linguistique en signal métier exploitable.

## 9. Exemple

Entrée :

```text
ياك عندي اوريدو كفاش ندير 5 دقايق باطل
```

Sortie :

```json
{
  "schema_version": "0.1.0",
  "is_exploitable": true,
  "non_exploitable_reason": null,
  "business_relevance": "directe",
  "language": {
    "dominant": "darija_arabe",
    "detected": ["darija"],
    "code_switching": false,
    "scripts": ["arabe", "chiffres"]
  },
  "entities": [
    {
      "id": "ent_1",
      "type": "marque",
      "name": "Ooredoo",
      "mention": "اوريدو",
      "start": 9,
      "end": 15,
      "source": "texte"
    }
  ],
  "sentiment": {
    "label": "neutre",
    "intensity": "faible",
    "emotion": "aucune",
    "sarcasm": false,
    "target_entity_ids": ["ent_1"],
    "evidence": [
      {
        "text": "كفاش ندير 5 دقايق باطل",
        "start": 16,
        "end": 38
      }
    ]
  },
  "intents": ["question", "demande_information"],
  "aspects": [
    {
      "family": "prix_valeur",
      "attribute": "promotion",
      "target_entity_id": "ent_1",
      "sentiment": "neutre",
      "intensity": "faible",
      "implicit": false,
      "evidence": [
        {
          "text": "5 دقايق باطل",
          "start": 26,
          "end": 38
        }
      ]
    }
  ],
  "alerts": [],
  "actionability": {
    "actionable": true,
    "queue": "service_client",
    "priority": "moyenne"
  }
}
```

## 10. Confiance et provenance

La confiance ne doit pas être une valeur inventée par le SLM. Elle doit être ajoutée par le pipeline à partir de :

- probabilités ou log-probabilités ;
- accord entre plusieurs générations ;
- accord entre teacher models ;
- validation par règles ;
- validation humaine.

L'enveloppe du dataset doit conserver séparément :

- `record_id`
- `text`
- contexte de collecte
- annotation
- source et licence/provenance
- type de donnée : réelle, teacher ou synthétique
- modèle teacher
- version du prompt
- version du schéma
- statut de revue
- split d'entraînement

## 11. Passage du Lot 1 au nouveau schéma

1. Conserver le Lot 1 actuel comme archive `silver_raw`.
2. Ne pas convertir automatiquement les 2 784 libellés libres par simple remplacement lexical.
3. Régénérer les annotations avec le JSON Schema V0.1 et le contexte de collecte.
4. Rejeter toute preuve dont `text != commentaire[start:end]`.
5. Revoir humainement tous les exemples mixtes, sarcastiques, alertes, non exploitables et désaccords teacher/label source.
6. Mesurer la couverture de chaque famille et attribut.
7. Réviser l'ontologie si un groupe cohérent de cas ne peut pas être représenté.
8. Geler la V1 avant le fine-tuning final.

## 12. Critères de validation avant entraînement

- 100 % de JSON valides ;
- 100 % de valeurs dans les enums ;
- 100 % de preuves vérifiées par offsets ;
- aucune marque ou produit halluciné ;
- accord inter-annotateurs mesuré sur un échantillon stratifié ;
- test réel séparé par source et par conversation ;
- Macro-F1 par sentiment, intention et aspect ;
- taux de sortie JSON exacte ;
- calibration de confiance ;
- latence et coût par commentaire.

## 13. Benchmark gold candidat V0.1

Un benchmark tenu hors entraînement a été constitué à partir de 100 commentaires :

- 95 commentaires issus des corpus réels ;
- 5 cas contrôlés pour couvrir des aspects rares ;
- 63 annotations corrigées pendant la revue experte ;
- 37 annotations acceptées après revue ;
- 100/100 conformes au schéma ;
- 100/100 preuves et offsets vérifiés ;
- 100/100 références d'entités valides.

Les lignes portent le split `gold_evaluation`. Les anciens labels faibles sont conservés uniquement dans la provenance et ne doivent jamais être fournis au modèle.

Le statut reste `single_reviewer_gold_candidate`. Une seconde annotation indépendante et une adjudication sont nécessaires avant de publier ce benchmark comme gold humain définitif.

Fichiers associés :

- `data/processed/slm_v2_gold/business_comments_gold_candidate_v0.1.jsonl`
- `docs/slm_v2/gold_v0.1/DATASET_CARD.md`
- `docs/slm_v2/gold_v0.1/REVIEW_RUBRIC.md`
- `docs/slm_v2/gold_v0.1/review_audit.jsonl`
- `scripts/evaluate_business_annotations_v01.py`

## 14. Split DEV/TEST et baseline teacher

Le gold candidat est séparé de manière déterministe et stratifiée :

- `gold_dev` : 50 commentaires pour améliorer le prompt et le validateur ;
- `gold_test` : 50 commentaires verrouillés pour l'évaluation finale ;
- chevauchement : 0 ;
- les deux splits restent strictement exclus de l'entraînement.

La baseline de `gemini-3.5-flash-lite`, évaluée de bout en bout sur les 100 cas,
obtient 90 % de sorties entièrement valides, 0,851 de Micro-F1 sur les intentions,
0,674 sur les aspects et seulement 0,278 de précision sur les alertes.

Décision : le teacher peut préparer des brouillons, mais la génération massive
reste bloquée jusqu'au passage des portes définies dans :

- `docs/slm_v2/gold_v0.1/baselines/BASELINE_GEMINI_3.5_FLASH_LITE.md`
- `docs/slm_v2/gold_v0.1/baselines/acceptance_gates_v0.1.json`
