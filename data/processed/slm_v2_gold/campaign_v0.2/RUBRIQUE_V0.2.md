# Rubrique d'annotation — Campagne V0.2

Contrat : `business-comment-annotation/0.2.0`

## Ce qui change par rapport à la V0.1

Ces règles viennent d'une mesure d'accord entre deux annotateurs indépendants. Elles
corrigent des ambiguïtés réelles du contrat précédent, pas des erreurs d'annotateur.

1. **`monitoring_target` est fourni en entrée.** Tu ne le décides jamais, tu ne le
   modifies jamais. Il détermine ce que tu as le droit d'annoter.
2. **Aucun aspect neutre.** Un aspect n'existe que s'il porte une charge évaluative.
3. **`attribute` est optionnel.** En cas d'hésitation, omets-le et garde la famille.
4. **`actionability` n'est plus annoté.** Le pipeline le calcule. Ne le produis pas.
5. **Nouveaux champs** : `author_role`, `requires_parent_context`.

---

## 0. Lire `monitoring_target` en premier

C'est la première chose à regarder, avant même le texte.

### `scope = organisation`

Une entité précise est surveillée (`entity_name`). Tu peux :

- poser des alertes ;
- utiliser `business_relevance = directe` si le commentaire vise cette entité.

### `scope = espace_public`

Aucune entité surveillée. Le commentaire est un signal de marché ou de société.

- **`alerts` doit rester vide.** Toujours. Même pour un contenu grave.
- **`business_relevance ∈ {indirecte, aucune}`.** Jamais `directe`.
- Les aspects restent possibles : c'est ainsi qu'on capture le signal.

Une pénurie d'eau dans une wilaya, une critique du système de santé, une protestation
étudiante : ce sont des signaux `indirecte` avec aspects, **pas des alertes**. Une
alerte suppose une organisation surveillée capable d'agir.

### `scope = secteur`

Non utilisé dans cette campagne. Si tu le rencontres, traite-le comme `espace_public`
et signale-le dans `notes`.

---

## 1. `author_role`

Qui parle ?

- `consommateur` : un particulier — le cas courant.
- `marque` : l'entité surveillée elle-même. Réponse officielle, communiqué, service
  client de la page. **Impose `sentiment = neutre`** : un communiqué d'une marque sur
  elle-même n'est pas un retour consommateur et ne doit pas alimenter ses métriques.
- `moderateur` : modération de la page.
- `media`, `institution` : compte de presse ou institutionnel.
- `inconnu` : indéterminable.

Indices de `marque` : « nous confirmons », « notre équipe », « veuillez nous contacter
en privé », réponse nominative à un client, ton institutionnel à la première personne
du pluriel au nom de l'entreprise.

## 2. `requires_parent_context`

Mets `true` lorsque la polarité dépend d'un post parent que tu n'as pas, typiquement
un commentaire très court répondant à une question invisible.

Exemples : `ZERO ✅️`, `حنا صحاب 4G رانا غايا 😂😂`.

Conséquences imposées par le schéma : `sentiment = neutre` et aucune alerte.

**Ne t'en sers pas comme échappatoire.** Un commentaire court mais autoporteur
(« Ma limonade préférée ») ne requiert aucun contexte. Le critère est : deux lecteurs
raisonnables liraient-ils la polarité différemment sans le post parent ?

## 3. Exploitabilité

Exploitable = le texte, ou le contexte, permet une décision fiable.

- Formule sociale sans objet business (prière, salutation) : `hors_sujet`.
- Un terme isolé ambigu ne devient pas une opinion.
- Une marque connue par la collecte identifie la cible, mais n'invente ni produit, ni
  aspect, ni sentiment.
- Si non exploitable : aucun aspect, aucune alerte, `business_relevance = aucune`.

## 4. Pertinence business

- `directe` : vise l'entité surveillée. **Réservé au scope `organisation`.**
- `indirecte` : marché, contexte socio-économique, emploi, réputation sectorielle,
  politique publique.
- `aucune` : aucun signal exploitable.

## 5. Langue

- `dominant` = la langue qui porte le sens, pas celle qui a le plus de caractères.
- `darija_arabizi` = darija en caractères latins et chiffres (3, 7, 9…).
- `code_switching = true` seulement en cas d'alternance réelle, pas pour un emprunt isolé.

## 6. Entités

- Écrite dans le texte : `source = texte`, `mention` = citation exacte.
- Connue par le contexte seulement : `source = contexte`, `mention = null`.
- Pays, ville, wilaya : `lieu`.
- Aucune inférence sans preuve. Ignorer les personnes taguées sans rôle dans l'opinion.

## 7. Sentiment

- Porte sur la cible business évaluée, **pas sur l'humeur générale du texte**.
  Un commentaire qui exprime un espoir personnel tout en constatant qu'il n'y a pas
  d'avenir professionnel dans le pays est négatif : la cible business est l'emploi.
- Une question pure reste `neutre`, sauf formulation clairement critique ou élogieuse.
- `mixte` exige un signal positif **et** un négatif visant la cible pertinente.
  Ne pas utiliser `mixte` pour un texte simplement nuancé.
- `sarcasm = true` seulement si le décalage est raisonnablement identifiable **sans**
  le post parent. Sinon, `requires_parent_context = true`.

## 8. Intentions

Trois maximum. Priorité : action principale (`plainte`, `question`, `suggestion`,
`signalement_incident`), puis acte évaluatif (`avis`, `eloge`, `recommandation`), puis
`partage_experience` s'il apporte une information distincte.

Une phrase déclarative n'est pas une `demande_information`.

## 9. Aspects

- **Aucun aspect neutre.** S'il n'y a pas de charge évaluative, il n'y a pas d'aspect.
- Annoter le minimum nécessaire au sens explicite.
- Une preuve ne porte qu'un seul aspect. Pas deux aspects synonymes sur le même extrait.
- `attribute` optionnel : en cas d'hésitation, garde la famille, omets l'attribut.
- En hésitation entre deux familles, choisis celle qui décrit **ce sur quoi porte le
  jugement**, pas le domaine général du commentaire.
- `implicit = true` seulement si le jugement est évident sans être formulé.

## 10. Alertes

Réservées au scope `organisation`. Une alerte exige un **risque concret pour l'entité
surveillée** :

sécurité ou santé · fraude ou arnaque · rupture de service ou de stock notable ·
risque juridique · confidentialité · harcèlement ou discrimination ·
crise réputationnelle vraisemblablement virale.

**Préséance** : si un risque d'ingestion ou de santé est en jeu, l'alerte est
`securite_sante`, même si un défaut qualité est aussi présent. Un produit alimentaire
avarié est d'abord un risque sanitaire.

Une accusation publique de tromperie visant l'entité surveillée (concours truqué,
publicité mensongère) **est** une alerte, même isolée : elle engage sa crédibilité.

Un mécontentement ordinaire, une plainte de prix, une déception banale n'en sont pas.
En cas de doute : pas d'alerte.

Sévérité : `faible` signal limité · `moyenne` incident réel circonscrit ·
`elevee` risque sérieux pour plusieurs personnes ou la continuité de service ·
`critique` danger grave, fraude majeure ou menace immédiate.

## 11. Preuves

Citations **exactes et contiguës**, copiées caractère pour caractère, aussi courtes que
possible. Ni normalisation, ni correction orthographique, ni retrait d'emoji.

**Ne calcule aucun offset.** Le pipeline s'en charge.
