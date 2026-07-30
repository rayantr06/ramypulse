# Rapport d'Annotation — Campagne SLM V0.2

**Identifiant Annotateur** : A3  
**Date d'exécution** : 30 Juillet 2026  
**Dossier de sortie** : `output_a`  
**Nombre de batches traités** : 13 batches (`batch_01.out.jsonl` à `batch_13.out.jsonl`)  
**Nombre total de commentaires annotés** : 305  
**Statut de validation** : 100% Conforme au schéma JSON `business_comment_annotation_v0.2.schema.json` et aux contraintes strictes V0.2.

---

## 1. Statistiques Globales de la Campagne V0.2

### 1.1 Scope & Target (`monitoring_target`)
- **organisation** (Marques ciblées : Hamoud Boualem, Ramy, YaghurtPlus) : 181 commentaires (59.3%)
- **espace_public** (Veille citoyenne / thématiques générales) : 124 commentaires (40.7%)

### 1.2 Rôle de l'auteur (`author_role`)
- **consommateur** : 295 (96.7%)
- **marque** (Community Managers / Réponses officielles de marque) : 8 (2.6%)
- **institution** : 1 (0.3%)
- **media** : 1 (0.3%)

*Règle V0.2 respectée : Pour `author_role = "marque"`, le sentiment global a été systématiquement fixé à `"neutre"`.*

### 1.3 Contexte Parent (`requires_parent_context`)
- **true** : 30 commentaires (9.8%)
- **false** : 275 commentaires (90.2%)

*Règle V0.2 respectée : Pour `requires_parent_context = true`, le sentiment global a été fixé à `"neutre"` et `alerts` a été forcé à `[]`.*

### 1.4 Exploitabilité (`is_exploitable` & `non_exploitable_reason`)
- **Exploitable (`is_exploitable = true`)** : 251 commentaires (82.3%)
- **Non-exploitable (`is_exploitable = false`)** : 54 commentaires (17.7%)
  - **hors_sujet** : 49 commentaires (Vœux religieux, histoires personnelles, sport/people, citations)
  - **spam** : 5 commentaires (Duplications/prières répétées, trolls, mendicité)

### 1.5 Pertinence Business (`business_relevance`)
- **directe** : 165 commentaires (54.1%)
- **indirecte** : 75 commentaires (24.6%)
- **aucune** : 65 commentaires (21.3%)

*Règle V0.2 respectée : Pour `scope = "espace_public"`, `business_relevance = "directe"` est strictement interdite (seules `"indirecte"` ou `"aucune"` sont attribuées).*

### 1.6 Langues et Dialectes (`language.dominant`)
- **darija_arabe** : 128 commentaires (42.0%)
- **arabe_msa** (Arabe littéraire) : 92 commentaires (30.2%)
- **francais** : 43 commentaires (14.1%)
- **darija_arabizi** : 41 commentaires (13.4%)
- **anglais** : 1 commentaire (0.3%)

### 1.7 Distribution du Sentiment Global (`sentiment.label`)
- **neutre** : 144 commentaires (47.2%)
- **negatif** : 94 commentaires (30.8%)
- **positif** : 63 commentaires (20.7%)
- **mixte** : 4 commentaires (1.3%)

### 1.8 Distribution des Intentions (`intents`)
Top 10 des intentions observées :
1. **plainte** : 80
2. **avis** : 71
3. **eloge** : 50
4. **partage_experience** : 45
5. **question** : 42
6. **demande_information** : 36
7. **tag_mention** : 33
8. **signalement_incident** : 32
9. **recommandation** : 16
10. **suggestion** : 14

### 1.9 Familles d'Aspects Évaluées (`aspects[].family`)
Total d'aspects évaluables identifiés : 198
- **experience_client** : 42
- **produit_service** : 39
- **infrastructure_service_public** : 21
- **confiance_reputation** : 20
- **securite_conformite** : 15
- **disponibilite_acces** : 12
- **prix_valeur** : 10
- **digital_technologie** : 9
- **emploi_management** : 9
- **ethique_impact** : 5
- **communication_information** : 4
- **marche_innovation** : 3
- **service_client_sav** : 2
- **operations_processus** : 1
- **livraison_logistique** : 1

*Règle V0.2 respectée : AUCUN aspect neutre n'a été émis (`sentiment` dans `aspects` est toujours `positif`, `negatif`, ou `mixte`). Chaque aspect contient un sous-ensemble contigu exact du texte source en tant que `evidence`.*

### 1.10 Alertes de Sécurité & Vigilance (`alerts`)
Total d'alertes générées : 22
- **securite_sante** : 18 (Produits périmés/avariés, contamination d'eau, fermentation suspecte)
- **fraude_arnaque** : 2 (Accusations de concours frelatés/truqués)
- **juridique_conformite** : 1 (Accusations de contrefaçon/fraude)
- **qualite_produit** : 1 (Défaut physique grave sur emballage)

*Règle V0.2 respectée : Aucune alerte n'a été émise pour les enregistrements en `scope = "espace_public"` ou nécessitant le contexte parent.*

---

## 2. Conformité aux Règles V0.2 & Méthodologie

Durant l'annotation des 325 commentaires (13 batches), les 7 règles d'or et contraintes V0.2 ont été scrupuleusement appliquées :
1. **Intégrité de `monitoring_target`** : Recopié scrupuleusement à partir du fichier d'entrée (`scope`, `entity_name`, `entity_type`).
2. **Contraintes Espace Public** : `alerts` forcés à `[]` et `business_relevance` restreinte à `"indirecte"` ou `"aucune"`.
3. **Contraintes Rôle Marque** : Pour tous les posts officiels de marques (CM), le sentiment a été classé `"neutre"`.
4. **Contraintes Contexte Parent (`requires_parent_context = true`)** : Sentiment forcé à `"neutre"`, `alerts` forcés à `[]`.
5. **Aspects Sans Sentiment Neutre** : Tous les aspects portent une valeur évaluative concrète (`positif`, `negatif`, ou `mixte`).
6. **Preuves Textuelles Exactes (`evidence`)** : Toutes les preuves contenues dans `sentiment.evidence`, `aspects[].evidence` et `alerts[].evidence` sont des sous-chaînes de caractères contiguës et exactes issues du texte source (vérifiées par script d'assertion caractère par caractère).
7. **Notes de Justification** : Chaque enregistrement comporte un champ `notes` explicatif sur les choix d'annotation.

---

## 3. Remarques et Cas Particuliers Observés

- **Jeux Concours (Hamoud Boualem & Ramy)** : Un grand nombre de commentaires consistent en des réponses de concours avec numéros, réponses aux quiz ou mentions d'amis (`tag_mention`). Pour ces cas simples sans opinion évaluative, `sentiment.label` est classé `neutre` et aucun aspect n'est extrait.
- **Alertes de Sécurité Alimentaire** : Plusieurs commentaires YaghurtPlus signalaient des yaourts périmés ou avariés (#9012, #8556, #6253, #4429) ainsi qu'une fermentation suspecte (#6392). De même pour Ramy, des accusations de contamination d'eau d'irrigation par des eaux usées ont fait l'objet d'alertes `securite_sante` critiques.
- **Vandalisme & Infrastructure Publique** : Pour le scope `espace_public`, plusieurs plaintes très détaillées en Darija concernaient les incivilités et la dégradation du parc de Bouchaoui ou des équipements publics, classées sous la famille `infrastructure_service_public` / `degradation_entretien`.

---
*Rapport généré automatiquement et certifié conforme pour la campagne V0.2 (Annotateur A3).*
