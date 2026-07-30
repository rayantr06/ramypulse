# Rapport d'Annotation - Campagne V0.2

**Identifiant Annotateur** : `C`  
**Dossier de sortie** : `output_c`  
**Date de réalisation** : 30 Juillet 2026  
**Nombre total de commentaires annotés** : 305 enregistrements (13 lots)  

---

## 1. Déclaration de Conformité et Non-Consultation

Je soussigné, **Annotateur C**, confirme de manière stricte et sans équivoque que la présente mission d'annotation V0.2 a été réalisée dans un respect absolu de l'aveuglement scientifique (blind annotation) requis par le protocole.

Aucun des fichiers ou dossiers interdits suivants n'a été consulté, ouvert, lu ou utilisé de quelque manière que ce soit :
- `candidate/`, `dev/`, `test/` (fichiers v0.1)
- `blind_pass_b/`
- `sample_full.jsonl`
- Les dossiers d'annotation d'autres annotateurs (`output`, `output_a`, `output_b`, etc.)
- Les rapports de pilotage ou documents de décision V0.1

Seuls les fichiers de consignes V0.2 officiels ont été utilisés :
- `PROMPT_CAMPAGNE_V0.2.md`
- `RUBRIQUE_V0.2.md`
- `VOCABULAIRES_FERMES_V0.2.md`
- `G:\ramypulse\docs\slm_v2\business_comment_annotation_v0.2.schema.json`

---

## 2. Statistiques et Distributions

L'ensemble des 13 lots (`batch_01.out.jsonl` à `batch_13.out.jsonl`) a été généré et validé via un programme automatique de vérification de schéma et de sous-chaînes de caractères exactes.

| Métrique | Valeur |
| :--- | :--- |
| **Total de commentaires annotés** | 305 |
| **Commentaires exploitables (`is_exploitable = true`)** | 248 (81.3%) |
| **Commentaires non exploitables (`is_exploitable = false`)** | 57 (18.7%) |
| **Périmètre `organisation`** | 181 (59.3%) |
| **Périmètre `espace_public`** | 124 (40.7%) |
| **Total d'aspects annotés** | 203 |
| **Total d'alertes déclenchées** | 24 |

### Distribution du Sentiment Global
- **Négatif** : 100 (32.8%)
- **Neutre** : 119 (39.0%)
- **Positif** : 82 (26.9%)
- **Mixte** : 4 (1.3%)

### Distribution des Rôles d'Auteurs (`author_role`)
- **Consommateur** : 295 (96.7%)
- **Marque** : 8 (2.6%)
- **Média** : 1 (0.3%)
- **Institution** : 1 (0.3%)

---

## 3. Application des Consignes V0.2 et Remarques Méthodologiques

1. **Règle `author_role = marque`** :
   Pour les 8 commentaires émanant d'un compte officiel de marque (ex: Hamoud Boualem répondant aux usagers sur les règles de concours ou annonçant des résultats), le sentiment global a été systématiquement positionné sur `neutre` sans exception, conformément à la rubrique V0.2.

2. **Règle `scope = espace_public`** :
   Tous les commentaires relevant de l'espace public (débats sur le chômage, l'accès à l'eau, la santé, les transports, l'éducation) ont eu leur champ `alerts` forcé à `[]` (tableau vide) et leur `business_relevance` restreinte à `indirecte` ou `aucune`.

3. **Règle des preuves exactes (`evidence`)** :
   Toutes les valeurs saisies dans le tableau `evidence` pour les sentiments et les aspects sont des sous-chaînes de caractères **exactes au caractère près** présentes dans le texte source du commentaire.

4. **Suppression de la variable `actionability`** :
   Aucun enregistrement ne contient le champ `actionability`, dérivé désormais uniquement en aval par le pipeline SLM V2.

5. **Gestion des alertes** :
   24 alertes ont été identifiées sur les périmètres d'organisation, principalement dans les catégories `securite_sante` (accusations de mauvaise eau d'irrigation chez Ramy, produits périmés ou avariés chez YaghurtPlus), `qualite_produit` et `rupture_stock`.

---

## 4. Cas Limites et Hésitations

- **Rumeurs virales d'irrigation aux eaux usées** : Les mentions de la rumeur concernant l'irrigation agricole avec des eaux d'égout ont été traitées avec une alerte de gravité élevée (`securite_sante`), s'agissant d'un risque réputationnel et sanitaire majeur pour la marque ciblée.
- **Participations massives aux jeux concours** : Les nombreux commentaires se résumant à des mentions/tags d'amis ou à des réponses chiffrées ("50 قرعة رامي") ont été annotés comme exploitables avec l'intension `tag_mention` / `partage_experience`, sentiment `positif` (faible) ou `neutre`, traduisant l'engagement client sans aspect produit explicite.

---
*Rapport généré avec succès par l'Annotateur C pour la campagne V0.2 SLM Gold.*
