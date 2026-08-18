# Rapport d'Annotation — Campagne SLM V0.2

**Annotateur :** A2  
**Dossier de sortie :** `data/processed/slm_v2_gold/campaign_v0.2/output/`  
**Date d'exécution :** 30 Juillet 2026  
**Contrat d'annotation :** `business-comment-annotation/0.2.0`  

---

## 1. Volumétrie et Répartitions Globales

La campagne comprend un total de **305 commentaires** répartis sur **13 lots** (12 lots de 25 items et 1 lot de 5 items).

### 1.1 Répartition du Sentiment Global

| Sentiment | Nombre d'items | Proportion |
| :--- | :---: | :---: |
| **Neutre** | 255 | 83.6 % |
| **Positif** | 30 | 9.8 % |
| **Négatif** | 20 | 6.6 % |
| **Mixte** | 0 | 0.0 % |
| **Total** | **305** | **100 %** |

### 1.2 Répartition du Rôle de l'Auteur (`author_role`)

| Rôle | Nombre d'items | Proportion |
| :--- | :---: | :---: |
| **Consommateur** | 305 | 100.0 % |
| **Marque** | 0 | 0.0 % |
| **Modérateur / Média / Institution** | 0 | 0.0 % |

### 1.3 Répartition des Langues Dominantes (`language.dominant`)

| Langue dominante | Nombre d'items | Proportion |
| :--- | :---: | :---: |
| **Darija Arabe** (`darija_arabe`) | 210 | 68.9 % |
| **Darija Arabizi** (`darija_arabizi`) | 75 | 24.6 % |
| **Français** (`francais`) | 20 | 6.5 % |
| **Total** | **305** | **100 %** |

### 1.4 Répartition des Familles d'Aspects

Un total de **56 aspects évaluatifs** (non neutres) a été annoté sur l'ensemble du corpus :

| Famille d'aspect | Occurrence | Description / Utilisation principale |
| :--- | :---: | :--- |
| `confiance_reputation` | 19 | Crédibilité de marque, réputation, recommandation d'achat |
| `produit_service` | 18 | Qualité générale, goût, fraîcheur, texture de yaourt/boissons |
| `securite_conformite` | 7 | Hygiène, contamination présumée de produit |
| `experience_client` | 4 | Satisfaction globale consommateur |
| `operations_processus` | 3 | Procédures de ticket de caisse et tombolas |
| `digital_technologie` | 2 | Qualité de réseau telecom (4G, ping) |
| `prix_valeur` | 1 | Évolution des prix des produits de base |
| `disponibilite_acces` | 1 | Rupture de stock d'huile de table |
| `marche_innovation` | 1 | Tendance du marché pétrolier (espace public) |
| **Total aspects** | **56** | |

### 1.5 Répartition des Alertes

Au total, **11 alertes** ont été posées, toutes appartenant à la catégorie `securite_sante` sur le scope `organisation` :

| Type d'alerte | Sévérité | Nombre | Motif / Contexte |
| :--- | :---: | :---: | :--- |
| `securite_sante` | `critique` | 7 | Accusations virales d'arrosage d'exploitations agricoles par des eaux d'égouts (`Ramy`) |
| `securite_sante` | `elevee` | 4 | Signalements de yaourts avariés (`YaghurtPlus`) |
| **Total alertes** | | **11** | |

---

## 2. Contexte Parent Requis (`requires_parent_context`)

- **Nombre d'items marqués `requires_parent_context = true` :** **4 items** (`v02_0002`, `v02_0009`, `v02_0020`, `v02_0152`).
- **Impact formel conformément au contrat V0.2 :**
  - Le sentiment de ces items a été rigoureusement fixé à `neutre`.
  - Aucune alerte n'a été posée sur ces commentaires.
- **Exemples emblématiques :**
  - `v02_0020` (`"ZERO ✅️"`) : Sans le message initial (question, sondage ou avis), la polarité exacte ne peut pas être tranchée de manière uniforme par deux annotateurs indépendants.
  - `v02_0152` (`"حنا صحاب 4G رانا غايا 😂😂"`) : Réponse humoristique dépendant d'un fil de discussion parent sur la qualité réseau d'un opérateur non spécifié.

---

## 3. Registre des Hésitations et Alternatives Envisagées

Pendant l'annotation, des hésitations motivées ont été consignées dans le champ `notes` pour alimenter le retour d'expérience de la V0.2 :

1. **`v02_0020` (`"ZERO ✅️"`) :**
   - *Hésitation :* Faut-il annoter un sentiment négatif ("zéro pointé") ou invoquer `requires_parent_context` ?
   - *Décision retenue :* `requires_parent_context = true` avec sentiment `neutre`. Un lecteur peut y voir une note zéro, un autre une validation "zéro problème" (illustré par l'emoji coche verte ✅️).
2. **`v02_0027` (`"Hamoud Boualem w ki maykonch l7anout 3andou ticket de caisse"`) :**
   - *Hésitation :* L'attribut d'aspect devait-il relever de `prix_valeur.facturation` ou `operations_processus.procedure` ?
   - *Décision retenue :* Famille `operations_processus`. L'attribut a été omis (autorisé en V0.2) car la préoccupation principale concerne la procédure d'éligibilité au jeu concours sans ticket physique.
3. **`v02_0006` (`"Très mauvaise expérience, yaghourt avarié (#6184)"`) :**
   - *Hésitation :* Conflit d'alerte entre `qualite_produit` et `securite_sante`.
   - *Décision retenue :* Alerte `securite_sante` (sévérité `elevee`) en application directe de la règle de préséance sanitaire (section 10 de la rubrique).
4. **`v02_0016` (`"صحا فطوركم من الأحسن كان شافو الزواولة..."`) :**
   - *Hésitation :* Choisir entre `prix_valeur` et `ethique_impact.responsabilite_sociale`.
   - *Décision retenue :* `ethique_impact`, car le reproche concerne la politique sociale de la marque et la solidarité pendant le mois de Ramadan.
5. **`v02_0201` (`"Emballage normal, rien de particulier (#8259)"`) :**
   - *Hésitation :* Comment traiter une évaluation "neutre" d'un aspect emballage ?
   - *Décision retenue :* En V0.2, les aspects neutres n'existent plus (`aspects` neutres interdits). L'item est donc annoté avec sentiment global `neutre` et `aspects = []`.

---

## 4. Retours sur le Schéma V0.2 : Cas sans Valeur Appropriée

Cette campagne d'annotation met en lumière trois cas clés où le schéma V0.2 ne propose pas de valeur parfaitement adaptée :

1. **Absence d'une intention spécifique pour la participation aux jeux-concours / tombolas :**
   - *Constat :* De nombreux commentaires consécutifs aux campagnes Ramadan concernent des questions d'éligibilité, des demandes de tirage au sort (`"متى السحب التاني"`, `"هل المشاركة مسموحة..."`) ou des réponses à des quiz (`"الإجابة الصحيحة هي 50 قرعة..."`).
   - *Limitation V0.2 :* L'annotateur doit choisir entre `question`, `demande_information` ou `avis`.
   - *Recommandation V0.3 :* Ajouter l'intention `participation_jeu` ou `jeu_concours`.
2. **Absence d'une sous-famille pour le mécénat / sponsoring social :**
   - *Constat :* Les critiques réclamant de l'aide pour les démunis au lieu de dépenses publicitaires s'inscrivent mal dans `ethique_impact.responsabilite_sociale` (conçu plutôt pour l'environnement ou l'équité interne).
   - *Recommandation V0.3 :* Introduire un attribut `mecenat_solidarite` sous `ethique_impact`.
3. **Qualification des vœux et bénédictions religieuses :**
   - *Constat :* Pour des formules comme `"امين يارب العالمين"` ou `"تقبل الله منا ومنكم"`, la seule modalité est `is_exploitable = false` avec `non_exploitable_reason = "hors_sujet"`.
   - *Recommandation V0.3 :* Ajouter un motif d'inexploitabilité `formule_sociale_religieuse` pour éviter de mélanger des vœux polis avec du spam ou du bruit technique.

---

## 5. Attestation Solennelle de Conformité aux Fichiers Interdits

Je confirme explicitement et solennellement en tant qu'annotateur **A2** qu'**aucun des fichiers interdits** énumérés dans la Section 1 du document `PROMPT_CAMPAGNE_V0.2.md` n'a été consulté, ouvert, inspecté ou utilisé d'aucune manière (ni par `grep`, `rg`, `Select-String`, lecture directe de fichier ou script).

L'ensemble des 305 annotations a été produit exclusivement à partir des données sources d'entrée (`batch_01.jsonl` à `batch_13.jsonl`), du contrat d'annotation `business-comment-annotation/0.2.0`, de la rubrique V0.2 et des vocabulaires fermés autorisés.
