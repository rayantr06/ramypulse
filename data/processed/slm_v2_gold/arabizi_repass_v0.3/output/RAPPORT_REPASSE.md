# Rapport de Réannotation Ciblée — Arabizi (V0.3)

**Identifiant Annotateur :** R1  
**Date :** 2026-07-30  
**Volume Total Annoté :** 61 commentaires (Batch 1: 21, Batch 2: 21, Batch 3: 19)

---

## 1. Répartition des Sentiments

### Répartition Globale (61 commentaires)

| Sentiment | Nombre | Pourcentage |
|---|---|---|
| **Négatif** | 33 | 54.1% |
| **Positif** | 15 | 24.6% |
| **Neutre** | 13 | 21.3% |
| **Mixte** | 0 | 0.0% |

### Répartition pour les seuls commentaires Arabizi (`darija_arabizi`: 39 commentaires)

| Sentiment | Nombre | Pourcentage |
|---|---|---|
| **Négatif** | 21 | 53.8% |
| **Positif** | 13 | 33.3% |
| **Neutre** | 5 | 12.8% |
| **Mixte** | 0 | 0.0% |

*Note de correction :* Le taux de `neutre` sur l'arabizi est passé de 54% (passe précédente biaisée) à 12.8% grâce à la méthode de traduction explicite `lecture_fr`.

---

## 2. Nombre d'Alertes par Type

| Type d'Alerte | Nombre | Exemples de motifs |
|---|---|---|
| `securite_sante` | 4 | Signalements réitérés d'irrigation avec eau d'égouts (risques sanitaires) |
| `qualite_produit` | 1 | Produit non frais à l'achat, DLC trop proche |
| `rupture_stock` | 2 | Rupture de stock lors de la prise de commande |
| `reputation_virale` | 1 | Perte de confiance manifeste / contestation sur promotion |

*Remarque :* Conformément au schéma V0.3, toutes les alertes ont été émises sous le scope `organisation`. Aucun niveau `critique` n'a été produit (niveaux autorisés : `faible`, `moyenne`, `elevee`).

---

## 3. Commentaires non déchiffrés

- **Aucun commentaire totalement indéchiffrable.**
- L'ensemble des 61 commentaires a pu être traduit fidèlement en français dans le champ `lecture_fr`.
- Les formes en chiffres arabizi (3=ع, 7=ح, 9=ق, 5=خ, etc.) et les abréviations populaires (bzf, nchalh, mli7, nemam, zmar, 3ayb, etc.) ont toutes été déchiffrées avec précision.

---

## 4. Cas aux limites du Contrat V0.3

- **Harcèlement et insultes explicites en `espace_public` :** Le commentaire `v02_0120` contient des propos à caractère sexuel explicites et vulgaires ciblant une personne nommée ("Yasmine", "tli9 pornstar"). Sous le scope `espace_public`, le schéma V0.3 interdit de poser une alerte `harcelement_discrimination`. Conformément à la section 6 du prompt, le sentiment a été codé comme `negatif` avec émotion `degout`, reflétant l'agressivité du propos tout en respectant l'interdiction d'alerte en `espace_public`.
- **Insultes personnelles sans entité surveillée :** Les commentaires `v02_0296` ("Nchallah rabi yeblik bmardh...") et `v02_0215` ("ya zmar rouh 3lina...") sont des insultes/agressions explicites. Ils ont été correctement qualifiés de sentiment `negatif` et restent exploitables.

---

## 5. Attestation de Conformité et Respect des Règles

- **Consultation des fichiers interdits :** Je confirme n'avoir ouvert, lu ou consulté **aucun** des fichiers interdits mentionnés en Section 1 (`_cle_ne_pas_ouvrir.json`, `human_validation_v0.3`, `blind_pass_b`, etc.).
- **Indépendance d'annotation :** Chaque commentaire a été traduit et évalué individuellement sans recours à des règles scriptées par mots-clés ni valeurs par défaut de masse.
- **Auto-contrôle :** 
  - 100% des lignes comportent un champ `lecture_fr` complet et pertinent.
  - 100% des commentaires qualifiés de `neutre` sont accompagnés d'une justification explicite dans `notes`.
  - 100% des preuves textuelles (`evidence`) sont des extraits exacts du texte original.
  - Aucun bloc `actionability` ni calcul d'offsets n'a été produit.
