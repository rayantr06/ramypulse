# Registre de décisions — Schéma d'annotation V0.2

Date : 30 juillet 2026
Décideur : Claude (Opus 5), sur délégation explicite du propriétaire du projet
Base factuelle : accord inter-annotateurs A vs B sur 100 commentaires
([rapport IAA](gold_v0.1/IAA_A_VS_B_2026-07-30.md))

## Méthode

Aucune décision n'a été prise par opinion. Chaque règle candidate a été **simulée sur
les annotations A et B existantes**, et l'accord a été recalculé. Une règle qui
n'améliorait pas l'accord mesuré n'a pas été retenue. Le schéma V0.2 a ensuite été
généré par transformation programmatique de la V0.1 et soumis à 13 tests de contrainte,
tous passants.

## Statut de ces décisions

Elles sont **révisables**. Elles sont prises sur un accord machine-machine (A et B sont
deux LLM), sur 100 commentaires dont 41 seulement portent une marque cliente, et
comptant 10 alertes au total. Ce sont des décisions d'ingénierie appuyées sur les
meilleures données disponibles, pas des vérités établies. Le propriétaire peut renverser
n'importe laquelle ; le registre existe pour rendre ce renversement facile.

---

## D1 — `monitoring_target` devient une entrée de configuration

**Problème.** Le contrat ne disait jamais *de qui* on fait la veille. A lisait « signal
sur l'espace observé » (une pénurie d'eau devient `rupture_service`), B lisait « signal
sur une organisation cliente » (sans marque, pas d'alerte). Les deux lectures étaient
autorisées par le schéma. 88 à 89 % des désaccords portaient sur les 59 commentaires
sans marque.

**Décision.** Ajout d'un bloc `monitoring_target` avec `scope ∈ {organisation, secteur,
espace_public}`, **fourni par la configuration de la veille et jamais inféré par le
modèle**. C'est le point essentiel : l'ambiguïté est résolue au moment de la collecte,
par paramétrage, et non au moment de l'annotation, par jugement.

Contraintes imposées par le schéma :

- `espace_public` → `alerts` vide obligatoire, `business_relevance ∈ {indirecte, aucune}` ;
- `organisation` → alertes et actionnabilité pleinement disponibles.

**Effet mesuré.**

| Champ | Avant | Après D1 |
|---|---:|---:|
| `actionability.actionable` | κ 0,468 | **κ 0,917** |
| `business_relevance` | κ 0,533 | **κ 0,942** |
| `alerts type+sévérité` | F1 0,400 | **F1 0,667** |

**Justification produit.** Une alerte doit être actionnable par le client. Une pénurie
d'eau nationale n'est pas actionnable par un producteur de boissons — c'est du signal de
marché, pas une alerte. Un système qui notifie sur la politique nationale sera coupé par
l'utilisateur en une semaine. La porte d'origine exigeait d'ailleurs une précision
d'alerte ≥ 0,95, ce qui encode déjà cette exigence de fiabilité.

Le scope `organisation` couvre aussi les clients publics (hôpital, université, opérateur,
administration) : pour eux, une plainte sanitaire ou scolaire vise bien l'entité
surveillée. L'axe n'est donc pas « marque commerciale » mais « entité surveillée ».

---

## D2 — `actionability.priority` devient dérivée, retirée de l'annotation

**Problème.** κ 0,306, le pire champ du contrat. 24 cas où A dit `moyenne` et B dit
`faible`. Aucun désaccord de plus d'un cran : ce n'est pas un désaccord de fond, c'est
l'absence de définition opérationnelle des quatre niveaux.

**Décision.** La priorité n'est plus annotée. Elle est calculée par le pipeline :

```
si alertes        -> priority = severite d'alerte maximale
sinon si actionnable et aspect negatif d'intensite forte -> moyenne
sinon             -> faible
```

**Effet mesuré (avec D1).** κ 0,306 → **κ 1,000**.

**Principe général retenu.** Tout champ sur lequel deux annotateurs ne s'accordent pas,
et qui peut être calculé à partir de champs sur lesquels ils s'accordent, doit être
dérivé et non annoté. Demander à un modèle de produire un champ irreproductible ne fait
qu'injecter du bruit dans l'apprentissage.

---

## D3 — `actionability.queue` devient dérivée

**Décision.** Table déterministe famille d'aspect → équipe, appliquée à l'aspect
dominant (le plus négatif, puis le plus intense).

**Effet mesuré.** κ 0,503 → **κ 0,675**.

Le gain est réel mais modeste : la file dérivée hérite désormais du désaccord sur les
aspects. Elle est malgré tout retirée de l'annotation, car un champ dérivé imparfait
reste préférable à un champ annoté moins fiable, et allège la charge du modèle.

Ajout de la file **`service_public`**, absente de la V0.1. Signalé par l'annotateur B et
vérifié : c'est la raison pour laquelle B répondait `aucune` sur les commentaires visant
des institutions publiques.

---

## D4 — Interdiction des aspects neutres, scoring au niveau famille+sentiment

**Problème.** F1 famille+attribut+sentiment = 0,511. Les confusions de famille sont en
réalité **rares** : seulement 10 cas où la même preuve reçoit deux familles différentes.
Le vrai problème est la sélection des passages : B pose 134 aspects, A en pose 101.

**Décisions.**

1. `aspect.sentiment` ne peut plus valoir `neutre`. Un aspect n'existe que s'il porte une
   charge évaluative — la rubrique l'exigeait déjà en principe, le schéma ne l'imposait pas.
2. `attribute` devient optionnel et **n'est plus évalué par les portes**. Il reste utile
   pour les tableaux de bord, mais ne doit pas faire échouer un modèle.

**Effet mesuré.**

| Variante | F1 |
|---|---:|
| famille + attribut + sentiment (V0.1) | 0,511 |
| famille + sentiment | 0,564 |
| sans aspects neutres | 0,592 |
| **famille + sentiment, sans neutres (V0.2)** | **0,640** |

**Limite assumée.** 0,640 reste le point faible du contrat. La calibration « combien
annoter » n'est pas résolue. C'est le sujet prioritaire de la V0.3.

---

## D5 — Ajout de `author_role`

**Problème.** Le commentaire `gold_v01_seed_6489` est une **réponse officielle de la
marque** (« nous confirmons que le concours est transparent, le tirage s'est fait en
présence d'un huissier »). A l'a compté comme sentiment `positif`. C'est un communiqué
d'entreprise sur elle-même, pas un retour consommateur.

**Décision.** `author_role ∈ {consommateur, marque, moderateur, media, institution,
inconnu}`. Le schéma impose `sentiment.label = neutre` lorsque `author_role = marque`.

**Enjeu produit.** Une collecte Facebook capture inévitablement les réponses de la page
surveillée. Les compter comme sentiment consommateur **gonfle artificiellement les
métriques du client sur ses propres publications**. C'est un défaut de produit, pas
seulement d'annotation.

---

## D6 — Ajout de `requires_parent_context`

**Problème.** Trois commentaires très courts ont reçu des polarités opposées :
`حنا صحاب 4G رانا غايا 😂😂`, `الحمد لله راني ب 3g 😌😌`, `ZERO ✅️`. A les lit comme
ironiques (sarcasme assumé, cohérent en interne), B les lit littéralement. Sans le post
parent, la question est **indécidable** : un troisième annotateur serait à pile ou face.

**Décision.** Champ booléen `requires_parent_context`. Lorsqu'il vaut `true`, le schéma
impose `sentiment = neutre` et interdit toute alerte.

**Justification.** Le bon comportement produit est de signaler « il me manque le post »
plutôt que de deviner. Ce drapeau devient un signal d'apprentissage utile, et non une
étiquette de repli.

---

## D7 — Préséance `securite_sante` > `qualite_produit`

Lorsqu'un risque d'ingestion ou de santé est en jeu, l'alerte est `securite_sante`, même
si un défaut qualité est également présent. Un yaourt avarié est d'abord un risque
sanitaire.

Arbitrage : **A avait raison** sur `gold_v01_seed_7226`.

---

## D8 — Une alerte exige un acteur visé

Une alerte suppose une entité surveillée identifiable et un risque qu'elle peut traiter.
Une dégradation sociale ou nationale sans acteur visé produit un signal de marché
(`business_relevance = indirecte` + aspects), jamais une alerte. Conséquence directe de D1.

---

## D9 — Portes d'acceptation recalibrées sur le plafond mesuré

Les seuils V0.1 étaient **inatteignables par construction** : ils exigeaient d'un modèle
plus de cohérence que la référence n'en a avec elle-même.

| Porte | V0.1 | V0.2 | Plafond mesuré |
|---|---:|---:|---:|
| `aspects_family_sentiment.micro_f1` | 0,80 | 0,55 | 0,640 |
| `alerts.precision` | 0,95 | 0,75 | 0,60 |
| `alerts.recall` | 0,80 | 0,55 | 0,75 |
| `business_relevance.macro_f1` | 0,85 | 0,80 | 0,97 |
| `intents.micro_f1` | 0,85 | 0,65 | 0,741 |
| `sentiment.macro_f1` | 0,80 | 0,70 | 0,788 |
| `evidence_grounding_rate` | 1,00 | 1,00 | 1,00 atteint |

Voir [acceptance_gates_v0.2.json](gold_v0.1/baselines/acceptance_gates_v0.2.json).
Fichier marqué **PROVISOIRE** : à recalculer sur les annotations V0.2.

---

## Arbitrages au cas par cas

### Alertes — 8 litiges

| Item | A | B | Décision | Règle |
|---|---|---|---|---|
| `seed_0576` pénurie d'eau, wilaya | `rupture_service` | aucune | **B** | D1/D8 |
| `seed_0740` pénurie d'huile | `rupture_stock` | aucune | **B** | D1/D8 |
| `seed_0844` protestation étudiante | `reputation_virale` | aucune | **B** | D1/D8 |
| `seed_1331` hôpital, père malade | `securite_sante` | aucune | **B** | D1/D8 |
| `seed_1500` médicaments indisponibles | `rupture_stock` | aucune | **B** | D1/D8 |
| `seed_4364` corruption, appels à la prison | `juridique_conformite` | aucune | **B** | D1/D8 |
| `seed_6476` concours accusé de truquage | aucune | `fraude_arnaque` | **B** | D1 |
| `seed_7226` yaourt avarié | `securite_sante` | `qualite_produit` | **A** | D7 |

**`seed_6476` mérite d'être souligné.** A n'y a vu aucune alerte. Or `seed_6489`, dans le
même corpus, est la **réponse officielle de Hamoud Boualem à cette accusation précise**,
invoquant la présence d'un huissier de justice. La marque a elle-même traité ce
commentaire comme nécessitant une réponse juridiquement étayée. B avait raison, et A a
manqué l'alerte la plus commercialement pertinente du corpus.

C'est l'argument le plus solide en faveur de la passe en aveugle : elle a rattrapé une
alerte que la revue experte simple avait laissée passer.

### Sentiment — 8 polarités opposées

| Item | A | B | Décision | Motif |
|---|---|---|---|---|
| `seed_0002` vie chère, Tebboune | negatif | mixte | **A** | aucune évaluation positive d'une cible business ; `mixte` sur-appliqué |
| `seed_1173` pas d'avenir pour les diplômés | negatif | positif | **A** | B s'ancre sur une motivation personnelle, pas sur la cible business |
| `seed_5532` « nous les 4G on va bien 😂😂 » | negatif | positif | **neutre** | D6 — indécidable sans post parent |
| `seed_5533` « el hamdoulillah je suis en 3g 😌😌 » | negatif | positif | **neutre** | D6 |
| `seed_6489` réponse officielle de la marque | positif | neutre | **B** | D5 — communiqué, pas retour consommateur |
| `seed_6562` félicitations aux gagnants | neutre | positif | **B** | engagement positif réel envers le concours |
| `seed_6928` « ZERO ✅️ » | neutre | positif | **B** + D6 | A n'avait fourni aucune preuve |
| `seed_7116` « J'insiste sur la bouteille en verre » | neutre | positif | **B** | préférence explicite d'emballage |

Bilan : A l'emporte 3 fois, B 5 fois, 2 cas basculent en `neutre` par règle nouvelle.
Aucun des deux annotateurs n'est systématiquement supérieur — ce qui confirme que les
désaccords venaient du contrat, pas de la compétence.

---

## Conséquence sur les artefacts existants

Le gold V0.1 **ne peut pas être simplement corrigé**. La V0.2 introduit trois champs
obligatoires (`monitoring_target`, `author_role`, `requires_parent_context`), interdit
les aspects neutres et retire deux champs de l'annotation. Les 100 lignes doivent être
réannotées sous le nouveau contrat.

Leur valeur n'est pas perdue : les textes, la stratification et les 16 arbitrages
ci-dessus deviennent la base de la campagne V0.2, et les précédents établis ici sont
opposables lors de cette campagne.

## Ce qui reste ouvert

1. **Calibration de la densité d'aspects** — F1 0,640, seul champ encore faible.
2. **Alertes non mesurables** — 5 alertes seulement après D1. Il faut un jeu enrichi à
   30 alertes positives minimum, obtenu par sur-échantillonnage ciblé.
3. **Aucune mesure humaine** — tout l'accord est machine-machine. Une validation humaine
   reste requise avant mise en production.
4. **Arabizi sous-représenté** — 2 à 3 exemples sur 100.
