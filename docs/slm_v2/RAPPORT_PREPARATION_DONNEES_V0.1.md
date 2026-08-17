# RamyPulse SLM V2 — Rapport de préparation des données V0.1

Date de gel : 29 juillet 2026  
Pipeline : `slm_v2_preparation_v0.1`  
Schéma business : `business-comment-annotation/0.1.0`

## Décision

Le socle de données V0.1 est préparé, reproductible et validé. Il peut servir :

- à l’adaptation linguistique en darija/arabizi ;
- aux tâches auxiliaires de sentiment et de toxicité ;
- à la constitution professionnelle du futur corpus d’annotation business.

Il ne suffit pas encore pour entraîner le SLM business final. Les 100 annotations
RamyPulse sont conformes au schéma, mais restent des **candidates mono-relecteur**.
Le pool business de 7 426 commentaires est prêt pour l’annotation, mais ses droits
d’usage doivent être décidés source par source avant tout entraînement commercial.

## Résultat global

| Mesure | Résultat |
|---|---:|
| Lignes déclarées | 79 723 |
| Lignes acceptées | 79 682 |
| Lignes rejetées avec motif | 41 |
| Clés textuelles exactes uniques | 79 375 |
| Pool d’annotation business | 7 426 |
| Gold candidates protégés | 100 |
| Vue linguistique CC-BY-4.0 | 56 652 |
| Vue linguistique CC-BY-SA-4.0 | 1 002 |
| Total des vues linguistiques entraînables | 57 654 |

## Sources enregistrées

| Source | Acceptées | Rejetées | Partition | Licence / statut |
|---|---:|---:|---|---|
| Algerian Dialect, Mendeley V2 | 45 000 | 0 | 36 037 train / 4 456 dev / 4 507 test | CC-BY-4.0 |
| AlgD Toxicity Speech | 14 150 | 0 | 11 417 train / 1 342 dev / 1 391 test | CC-BY-4.0 |
| Algerian Hirak Sentiment | 11 719 | 41 | 9 378 train / 1 093 dev / 1 248 test | CC-BY-4.0 |
| NArabizi UD | 1 287 | 0 | 1 003 train / 139 dev / 145 test publiés | CC-BY-SA-4.0 |
| RamyPulse business seed pool | 7 426 | 0 | annotation_pool uniquement | Droits non établis |
| RamyPulse business gold candidate | 100 | 0 | 50 gold_dev / 50 gold_test | Propriétaire, revue requise |

Références des sources publiques :

- Mendeley : <https://data.mendeley.com/datasets/zzwg3nnhsz/2>
- AlgD Toxicity : <https://zenodo.org/records/10937445>
- Hirak Sentiment : <https://zenodo.org/records/10937412>
- NArabizi UD : <https://github.com/UniversalDependencies/UD_Maghrebi_Arabic_French-Arabizi/tree/89fddb4adedb65beac28f56e548dba0b9ceec8d0>

## Normalisation appliquée

Le pipeline conserve les fichiers sources comme entrées immuables et produit des
artefacts dérivés. Il applique :

- Unicode NFC pour le texte d’entraînement et une forme NFKC séparée pour la déduplication ;
- suppression des contrôles invisibles et bidirectionnels ;
- remplacement des URL, e-mails, numéros de téléphone plausibles et identifiants `@user` ;
- conservation des empreintes SHA-256, du fichier source et de la ligne source ;
- conservation des labels originaux, plus une représentation normalisée ;
- séparation physique des vues selon la licence ;
- rejet explicite au lieu d’une correction silencieuse des données irréparables.

Les 100 annotations structurées gardent leur texte source exact dans l’espace de
revue afin de ne pas casser les offsets de preuve. Elles ne sont jamais exposées
dans une vue TRAIN.

## Labels publics normalisés

### Sentiment Mendeley

Le mapping publié est conservé :

| Valeur | Label |
|---:|---|
| 0 | très négatif |
| 1 | négatif |
| 2 | neutre |
| 3 | positif |
| 4 | très positif |

Distribution : 1 543 très négatifs, 14 414 négatifs, 10 093 neutres,
16 747 positifs et 2 203 très positifs.

### Sentiment Hirak

Le mapping publié est `0 = négatif`, `1 = positif`. Après exclusion des lignes
techniquement invalides : 5 637 négatives et 6 082 positives.

### Toxicité AlgD

Les trois annotations binaires sont conservées ensemble :

- hate speech ;
- cyberbullying ;
- offensive language.

Elles restent des tâches auxiliaires. Elles ne sont pas converties directement en
alertes business RamyPulse.

### NArabizi

Les splits publiés sont intacts. La valeur `offensive_classification` est conservée
comme valeur source brute, sans inventer une sémantique absente de la documentation
locale. La licence CC-BY-SA reste isolée de la vue CC-BY.

## Contrôles anti-fuite

| Contrôle | Résultat |
|---|---:|
| Groupes de doublons exacts | 290 |
| Lignes appartenant à ces groupes | 597 |
| Groupes exacts TRAIN ↔ évaluation | 9 |
| Paires quasi-dupliquées signalées | 209 |
| Paires quasi-dupliquées proches d’une évaluation protégée | 35 |
| Lignes TRAIN bloquées automatiquement pour quasi-duplication ≥ 0,98 | 30 |
| Groupes vidéo Mendeley traversant plusieurs splits | 0 |
| Enregistrements protégés encore entraînables | 0 |

La quasi-déduplication combine SimHash sur shingles de caractères et vérification
de similarité. Les 209 paires sont un **rapport d’audit**, pas une vérité
sémantique. Seules les 30 collisions à haute confiance avec une partition protégée
ont été automatiquement bloquées.

## Rejets et anomalies

Les 41 rejets proviennent du corpus Hirak :

- 40 textes contiennent le caractère Unicode de remplacement `�`, donc
  l’information d’origine est déjà perdue ;
- 1 cellule est mal formée et ne contient pas le couple `label,text`.

Six lignes des sources publiques et six lignes du pool business portent un drapeau
`possible_mojibake`. L’audit montre que plusieurs sont simplement des majuscules
accentuées valides (`ÂNE`, `ZAÂIM`) ; elles ne sont donc pas supprimées
automatiquement. Elles doivent faire partie de l’échantillon de contrôle humain.

## Pool business de 7 426 commentaires

Le pool est normalisé et dédupliqué, mais reste `annotation_pool` :

| Provenance | Lignes |
|---|---:|
| massinissa_algerian_corpus | 5 658 |
| ramypulse_v1_facebook | 1 566 |
| tenant_demo_expo | 200 |
| tenant_ramy_client | 2 |

Les anciens champs `sentiment_label` et `aspect` sont stockés sous
`legacy_weak_labels_not_for_model_target`. Ils peuvent équilibrer un échantillon,
mais ne doivent jamais devenir la réponse attendue du SLM.

Les droits du sous-corpus Massinissa et les droits d’exploitation des commentaires
de plateformes doivent être documentés avant une utilisation d’entraînement.
Jusqu’à cette décision, les 7 426 lignes sont autorisées uniquement pour la
sélection et la revue d’annotations.

## Évaluation des 100 gold candidates

Résultat mécanique :

- 100/100 valides selon le JSON Schema ;
- 100/100 avec offsets de preuve et références d’entités cohérents ;
- 50 protégés dans `gold_dev`, 50 dans `gold_test` ;
- 0 ligne admissible en entraînement ;
- 100/100 portent le statut `single_reviewer_gold_candidate`.

Couverture observée :

- 95 exploitables et 5 non exploitables ;
- langues dominantes : 47 darija arabe, 35 arabe MSA, 11 français,
  4 mixtes, 2 darija arabizi, 1 anglais ;
- sentiments : 46 négatifs, 31 neutres, 21 positifs, 2 mixtes ;
- 101 annotations d’aspect couvrant les 15 familles et 47 couples
  famille/attribut ;
- seulement 10 alertes, dont 2 critiques ;
- seulement 2 exemples dominants en arabizi ;
- 41 exemples sur 100 proviennent du thème FMCG boissons.

Conclusion : la largeur du schéma est démontrée, mais les classes rares, l’arabizi,
les alertes et plusieurs secteurs sont trop peu couverts. Les 100 lignes ne doivent
pas être utilisées comme preuve qu’un modèle généraliste est prêt.

## Quarantaine des anciennes générations

Les anciennes sorties OpenAI/Gemini n’ont pas été supprimées, mais elles sont
explicitement interdites pour TRAIN et EVAL dans
`data/registry/slm_v2_quarantine_v0.1.json`.

Point notable : le résultat brut OpenAI contient 3 000 lignes, alors que l’ancienne
vue d’entraînement dérivée n’en contient que 2 997. En plus de l’ancien schéma et
des traces `<think>` libres, cet écart justifie la quarantaine.

## Prochaine étape recommandée

La prochaine étape n’est pas encore le fine-tuning. C’est la création du vrai
corpus business V0.2 :

1. Faire une double annotation humaine et une adjudication des 100 candidates.
2. Tirer un pilote de 300 à 500 nouvelles lignes depuis `annotation_pool`, avec
   sur-échantillonnage de l’arabizi, des alertes, du non exploitable et des secteurs
   peu couverts.
3. Mesurer l’accord inter-annotateurs par champ et simplifier toute valeur qui
   reste ambiguë.
4. Geler ensuite un vrai `gold_dev` et un `gold_test` que les enseignants
   synthétiques ne verront jamais.
5. Générer les exemples synthétiques uniquement après ce gel, en `answer_only` et
   `compact_decision_trace`, puis garder le format qui améliore réellement le
   score sur le gold humain.

## Reproduction

```powershell
python scripts/acquire_slm_v2_corpora.py --verify-only
python scripts/prepare_slm_v2_corpora.py
python scripts/validate_slm_v2_corpora.py
```

La validation finale passe avec 79 682 enregistrements, 41 rejets conservés avec
motif, 43 545 groupes vidéo sans fuite et 57 654 lignes dans les vues linguistiques.
