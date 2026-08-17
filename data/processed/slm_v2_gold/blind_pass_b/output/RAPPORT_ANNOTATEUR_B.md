# Rapport d'Annotation — Annotateur B (Passe Indépendante en Aveugle)

**Date :** 30 Juillet 2026  
**Annotateur :** B  
**Corpus :** RamyPulse SLM V2 (`data/processed/slm_v2_gold/blind_pass_b/`)  
**Statut :** Mission accomplie avec succès.

---

## 1. Volumétrie Générale

- **Nombre total de commentaires annotés :** 100 commentaires (répartis en 5 batches de 20 commentaires).
- **Format de sortie :** JSONL (1 ligne par commentaire, UTF-8 sans BOM, ordre et `record_id` strictement identiques aux fichiers d'entrée).
- **Emplacements des fichiers générés :**
  - `data/processed/slm_v2_gold/blind_pass_b/output/batch_01.out.jsonl`
  - `data/processed/slm_v2_gold/blind_pass_b/output/batch_02.out.jsonl`
  - `data/processed/slm_v2_gold/blind_pass_b/output/batch_03.out.jsonl`
  - `data/processed/slm_v2_gold/blind_pass_b/output/batch_04.out.jsonl`
  - `data/processed/slm_v2_gold/blind_pass_b/output/batch_05.out.jsonl`

---

## 2. Statistiques et Répartition des Annotations

### 2.1 Exploitabilité et Pertinence Business

- **Exploitables (`is_exploitable: true`) :** 97 commentaires
- **Non exploitables (`is_exploitable: false`) :** 3 commentaires (tous classés `non_exploitable_reason: "hors_sujet"`, avec `business_relevance: "aucune"`, 0 aspect, 0 alerte)
  - `gold_v01_seed_6966` : Prière religieuse répétée de nombreuses fois sans lien business.
  - `gold_v01_seed_4671` : Prière en réponse à une mention sans portée business.
  - `gold_v01_seed_0041` : Formule de salutation courtoise ("نهاركم مبروك") isolée.
- **Pertinence business :**
  - `directe` : 44 commentaires (évaluations, réclamations ou questions visant directement une marque comme Hamoud Boualem, Ramy, YaghurtPlus ou Ooredoo).
  - `indirecte` : 53 commentaires (contexte socio-économique, infrastructures publiques, santé, emploi, pétrole).
  - `aucune` : 3 commentaires (non exploitables).

### 2.2 Sentiments Globaux

| Sentiment | Effectif | Proportion |
|---|---|---|
| **Négatif** | 42 | 42 % |
| **Neutre** | 29 | 29 % |
| **Positif** | 26 | 26 % |
| **Mixte** | 3 | 3 % |
| **Total** | **100** | **100 %** |

### 2.3 Répartition des Familles d'Aspect (129 aspects au total sur 97 commentaires exploitables)

| Famille d'aspect | Nombre d'occurrences | Attributs principalement mobilisés |
|---|---|---|
| `infrastructure_service_public` | 25 | `infrastructure`, `sante_publique`, `education`, `couverture_territoriale`, `eau_energie` |
| `prix_valeur` | 24 | `prix`, `promotion`, `rapport_qualite_prix`, `abordabilite`, `facturation` |
| `produit_service` | 15 | `qualite_generale`, `gout`, `emballage`, `fonctionnalite`, `fraicheur`, `design` |
| `digital_technologie` | 11 | `connexion_reseau`, `application`, `ergonomie`, `site_web` |
| `experience_client` | 9 | `fidelite`, `satisfaction_globale`, `attente`, `comportement_personnel`, `accueil` |
| `emploi_management` | 9 | `recrutement`, `salaire`, `conditions_travail`, `equite_interne` |
| `confiance_reputation` | 8 | `image_marque`, `credibilite`, `comparaison_concurrent`, `authenticite` |
| `disponibilite_acces` | 7 | `rupture`, `stock`, `couverture_geographique`, `canal_achat` |
| `ethique_impact` | 6 | `corruption`, `responsabilite_sociale`, `equite` |
| `marche_innovation` | 5 | `tendance`, `innovation`, `production_locale`, `positionnement` |
| `communication_information` | 4 | `clarte`, `transparence`, `publicite` |
| `securite_conformite` | 3 | `hygiene`, `securite` |
| `service_client_sav` | 3 | `reactivite`, `resolution` |
| `operations_processus` | 3 | `delai`, `capacite` |
| `livraison_logistique` | 2 | `distribution`, `suivi_commande` |

### 2.4 Alertes Rédhibitoires et Risques Critiques (5 alertes sur 100 commentaires)

Conformément à la rubrique, les alertes ont été strictement réservées aux risques majeurs (sanitaires, sécurité, réputation virale ou rupture critique) :

1. **`gold_v01_seed_5715`** (`Ramy`) :  
   - Type : `securite_sante` | Sévérité : `critique`  
   - Preuve : `"تسقي بالصرف الصحي"` (accusation d'irrigation de cultures par eaux d'égouts).
2. **`gold_v01_seed_5658`** (`Ramy`) :  
   - Type : `securite_sante` | Sévérité : `critique`  
   - Preuve : `"تيو مربوط بالزيڨو لي تسقو بيه المزرعة"` (accusation identique de raccordement d'irrigation au réseau d'assainissement).
3. **`gold_v01_seed_7226`** (`YaghurtPlus`) :  
   - Type : `qualite_produit` | Sévérité : `elevee`  
   - Preuve : `"yaghourt avarié"` (produit laitier avarié / problème de chaîne du froid).
4. **`gold_v01_seed_6476`** (`Hamoud Boualem`) :  
   - Type : `fraude_arnaque` | Sévérité : `moyenne`  
   - Preuve : `"مسابقة 1000% ماشي صح و ما فيها مصداقية"` (accusation publique de fausse tombola et manque de crédibilité).
5. **`gold_v01_seed_7224`** (`YaghurtPlus`) :  
   - Type : `rupture_stock` | Sévérité : `moyenne`  
   - Preuve : `"Rupture de stock trop fréquente"` (rupture de stock chronique récurrente).

### 2.5 Langues Dominantes

| Langue dominatale | Code schema | Nombre |
|---|---|---|
| Darija en écriture arabe | `darija_arabe` | 55 |
| Arabe Standard Moderne | `arabe_msa` | 32 |
| Français | `francais` | 10 |
| Darija en écriture latin/chiffres (Arabizi) | `darija_arabizi` | 3 |

---

## 3. Liste des Commentaires avec Hésitations et Décisions Arbitrées

Voici les cas où un arbitrage s'est avéré nécessaire, accompagnés de l'alternative envisagée et de la justification du choix final :

1. **`gold_v01_seed_7069`** (`حمود بوعلام البيضة اه اه اه مع اطباق الاسماك روعة ♥`)  
   - *Hésitation :* `produit_service/gout` vs `produit_service/qualite_generale`.  
   - *Décision :* `produit_service/gout` retenu car l'éloge porte spécifiquement sur le mariage gustatif entre la boisson et les plats de poisson.
2. **`gold_v01_seed_6176`** (`شاركت في طومبلا بصح قسيمة الشراء مكتوب فيها hamoud فقط هل هي مقبولة`)  
   - *Hésitation :* File d'actionabilité `service_client` vs `communication`.  
   - *Décision :* `service_client` retenu car il s'agit d'une question individuelle d'éligibilité nécessitant une assistance directe au participant.
3. **`gold_v01_seed_0212`** (`حتى الزيت راه طلع وناقص 🤔`)  
   - *Hésitation :* Attribut `disponibilite_acces/rupture` vs `disponibilite_acces/stock` pour la mention `"وناقص"`.  
   - *Décision :* `rupture` retenu car le terme exprime la pénurie et le manque d'approvisionnement sur le marché.
4. **`gold_v01_seed_6121`** (`علاه حنا غادي نشربوا الحلّة ؟`)  
   - *Hésitation :* `prix_valeur/rapport_qualite_prix` vs `produit_service/emballage`.  
   - *Décision :* `rapport_qualite_prix` retenu avec `sarcasm: true`, car l'auteur utilise l'ironie pour reprocher le surcoût de l'emballage par rapport au produit consommable.
5. **`gold_v01_seed_6759`** (`كمال الزئبق خطر كل يوم لازم تكون حاضرة فوق الطابلة`)  
   - *Hésitation :* `experience_client/fidelite` vs `produit_service/qualite_generale`.  
   - *Décision :* `fidelite` retenu pour qualifier l'incontournabilité quotidienne de la boisson sur la table familiale.
6. **`gold_v01_seed_6617`** (`الف مبروك.للاسف شاركت ومربحتش 💔`)  
   - *Hésitation :* Label de sentiment `mixte` vs `negatif`.  
   - *Décision :* `mixte` retenu car le commentaire contient simultanément une félicitation positive adressée aux gagnants et une déception personnelle exprimée pour sa propre perte.
7. **`gold_v01_seed_1632`** (`احسن منظومة صحية وزيدها هذا المشروع الظخم. الحمد لله...هذا خير كبير.`)  
   - *Hésitation :* Présence ou absence de sarcasme.  
   - *Décision :* `sarcasm: true` appliqué sur la formule `"احسن منظومة صحية"`, très fréquemment employée de manière ironique sur les réseaux sociaux algériens.
8. **`gold_v01_seed_6611`** (`Hamoud Boualem w ki maykonch l7anout 3andou ticket de caisse ?`)  
   - *Hésitation :* Attribut `prix_valeur/promotion` vs `disponibilite_acces/canal_achat`.  
   - *Décision :* Les deux aspects ont été annotés conjointement pour refléter le blocage lié aux habitudes de distribution traditionnelles (épiceries de quartier ne délivrant pas de ticket).
9. **`gold_v01_seed_0940`** (`ثمن الدوة وفي اي ولاية في الجزائر`)  
   - *Hésitation :* Traitement de la coquille manifeste (`"الدوة"` pour `"الدورة"`).  
   - *Décision :* Le commentaire a été jugé exploitable car l'intention d'achat et la demande d'information tarifaire/géographique sur la formation sont sans ambiguïté.

---

## 4. Retours sur le Schéma V0.1 et Limites Identifiées

La confrontation du schéma JSON `business-comment-annotation v0.1.0` au corpus réel d'opinions et de discussions algériennes fait ressortir quatre limites majeures :

1. **Absence de file d'actionabilité pour les services publics / secteur institutionnel :**  
   Le vocabulaire de `actionability.queue` (`produit`, `pricing`, `service_client`, `ventes`, `operations`, `logistique`, `digital`, `communication`, `rh`, `juridique_conformite`, `securite_qualite`, `direction`, `aucune`) est orienté exclusivement vers l'entreprise privée commerciale. Lorsqu'un commentaire concerne la santé publique, l'éducation nationale ou les transports, aucune file dédiée n'existe. Une catégorie `service_public` ou `institutionnel` manque au schéma.

2. **Manque d'attribut pour la dégradation du bien public / incivilités :**  
   Pour des commentaires dénonçant le vandalisme ou l'entretien des équipements publics (ex: bancs cassés à Bouchaoui `gold_v01_seed_5544` ou dégradation des places publiques `gold_v01_seed_3923`), la famille `infrastructure_service_public` propose l'attribut `infrastructure`, mais il n'existe pas d'attribut spécifique pour `entretien_maintenance` ou `degradation_incivilite`.

3. **Complexité d'annotation des jeux-concours et tombolas :**  
   Les campagnes de tombola génèrent de nombreuses interrogations pratiques (perte de ticket, absence de ticket de caisse chez l'épicier, bugs d'application de scan). Actuellement, ces commentaires sont partagés entre `prix_valeur/promotion`, `digital_technologie/ergonomie` et `communication_information/clarte`, sans attribut englobant les processus d'animation commerciale.

4. **Identification du locuteur officiel vs consommateur :**  
   Le schéma n'inclut pas de champ permettant de spécifier si l'auteur du texte est un consommateur, un journaliste (ex: dépêche économique sur l'OPEP `gold_v01_seed_0236`) ou le CM officiel de la marque (ex: réponse officielle d'Hamoud Boualem `gold_v01_seed_6489`).

---

## 5. Confirmation Explicite de Respect du Protocole en Aveugle

Je confirme de manière **explicite et absolue** qu'aucun fichier de la liste interdite :

- `data/processed/slm_v2_gold/business_comments_gold_candidate_v0.1.jsonl`
- `data/processed/slm_v2_gold/business_comments_gold_dev_v0.1.jsonl`
- `data/processed/slm_v2_gold/business_comments_gold_test_v0.1.jsonl`
- `data/processed/slm_v2_corpora/v0.1/normalized/ramypulse_business_gold_candidate.jsonl`
- `data/processed/slm_v2_pilot/**`
- `docs/slm_v2/gold_v0.1/review_decisions.jsonl`
- `docs/slm_v2/gold_v0.1/review_audit.jsonl`
- `docs/slm_v2/gold_v0.1/REVIEW_RUBRIC.md`
- `docs/slm_v2/gold_v0.1/baselines/**`
- `docs/slm_v2/pilot_reports/**`
- `docs/slm_v2/GUIDE_ANNOTATION_BUSINESS_V0.1.md`
- `data/processed/master_seed_7k.jsonl`

n'a été ouvert, lu, recherché (par `grep`, `rg` ou tout autre moyen) ni consulté de quelque façon que ce soit à aucun moment de la mission. 

Seuls les fichiers autorisés (`blind_pass_b/input/batch_01.jsonl` à `batch_05.jsonl`, `RUBRIQUE_PASSE_B.md`, `VOCABULAIRES_FERMES.md`, et `business_comment_annotation_v0.1.schema.json`) ont servi de base à cette annotation indépendante. Aucun script du dossier `scripts/` n'a été exécuté et aucun commit Git n'a été effectué.
