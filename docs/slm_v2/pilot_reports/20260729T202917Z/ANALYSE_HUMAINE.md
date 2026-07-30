# Analyse humaine du pilote — contrat business V0.1

## Décision

Le schéma métier V0.1 constitue une bonne base pour le SLM généraliste, mais le pipeline d'annotation n'est pas encore prêt pour une génération massive.

Le pilote valide les choix structurants suivants :

- catégories fermées et versionnées ;
- séparation entre sentiment global et sentiment par aspect ;
- aspects organisés en famille et attribut ;
- preuves textuelles rattachées au commentaire ;
- entités distinguant provenance textuelle et contexte de collecte ;
- alertes séparées des simples opinions négatives ;
- actionnabilité et routage métier.

Il ne justifie pas l'ajout de nouveaux libellés libres. Les principaux défauts observés relèvent du guidage du modèle, des offsets et du manque de contexte conversationnel.

## Protocole

Le test principal couvre 24 commentaires sélectionnés pour représenter :

- FMCG et marques algériennes ;
- prix, promotion, qualité, emballage et rupture de stock ;
- emploi, santé, éducation, télécom, tourisme et marché ;
- Darija arabe, Arabizi, arabe standard et français ;
- commentaires clairs, ambigus et hors sujet.

`gpt-5.4-mini` n'a pas pu être utilisé, le compte OpenAI retournant `429 insufficient_quota`. Gemini 2.5 Flash avait également épuisé son quota quotidien. Le test a donc été exécuté avec `gemini-3.5-flash-lite`. Les résultats évaluent le contrat et ce modèle enseignant précis ; ils ne préjugent pas de la qualité de `gpt-5.4-mini`.

## Résultats

### Premier passage sur 24 commentaires

| Mesure | Résultat |
|---|---:|
| Réponses API récupérées | 23/24 |
| Conformes au schéma avant correction | 15/23 |
| Conformes au schéma après correction des offsets | 15/23 |
| Conformes à tous les contrôles après correction | 15/23 |
| Sorties nécessitant un réalignement d'offset | 15/23 |
| Accord avec l'ancien sentiment faible | 17/23 |

Les huit non-conformités structurées provenaient principalement de couples famille/attribut incohérents. Un modèle pouvait par exemple produire `produit_service/promotion`, alors que `promotion` appartient à `prix_valeur`.

### Second passage ciblé après correction du pipeline

Le schéma de génération a été modifié pour présenter chaque famille avec sa propre liste d'attributs. Les anciens labels faibles de sentiment et d'aspect ont été retirés du contexte visible par le modèle. Les limites de tableaux, notamment trois intentions maximum, ont été conservées.

| Mesure | Résultat |
|---|---:|
| Réponses API récupérées | 10/10 |
| Conformes au schéma JSON métier | 10/10 |
| Conformes avant correction des offsets | 2/10 |
| Conformes après réalignement déterministe | 10/10 |
| Non-conformités famille/attribut | 0 |

Le passage de 65,2 % à 100 % de conformité finale sur les cas difficiles confirme que l'ontologie était suffisante : la représentation du contrat dans le prompt était le principal problème.

## Enseignements importants

### 1. Les offsets ne doivent pas être appris par le modèle enseignant

Huit sorties sur dix du second test contenaient de bonnes citations mais des indices Unicode inexacts. Le réalignement déterministe a corrigé 24 spans sans modifier leur contenu.

Décision recommandée :

- le modèle extrait la citation exacte ;
- le pipeline calcule `start` et `end` ;
- l'exemple n'entre dans le dataset que si `texte[start:end] == citation`.

Demander à un SLM de compter des caractères Unicode gaspille de la capacité et introduit du bruit évitable.

### 2. Les anciens labels faibles ne doivent jamais être visibles par l'enseignant

Le commentaire `ZERO ✅️` a été annoté négativement lorsque le modèle voyait l'ancien label `negatif`, puis positivement après retrait de ce label. Cette inversion montre un risque clair de fuite et d'ancrage.

Les anciens labels doivent être conservés uniquement pour l'évaluation comparative, jamais dans le prompt de génération.

### 3. Un JSON valide ne garantit pas une annotation juste

Plusieurs sorties conformes restent discutables :

- le signal sanitaire lié à l'irrigation par eaux usées a été classé `indirecte/neutre` sur un commentaire, mais `directe/negatif/critique` sur un commentaire presque équivalent ;
- `ZERO ✅️` reste trop ambigu pour conclure sans connaître le post parent ou le produit visé ;
- l'article sur le prix du pétrole a été classé en pertinence directe alors qu'une pertinence indirecte de veille marché est plus cohérente ;
- certains commentaires ironiques courts peuvent être mal lus sans contexte conversationnel.

Le prochain benchmark doit donc mesurer la justesse sémantique sur un jeu gold humain, et pas seulement la validité JSON.

### 4. Le contexte de collecte actuel est insuffisant pour certains commentaires

Une marque seule ne suffit pas toujours. Le format d'entrée devrait pouvoir fournir, lorsqu'ils existent :

- texte du post parent ;
- produit, campagne ou service concerné ;
- plateforme ;
- réponse à laquelle le commentaire réagit ;
- date et pays ;
- marque connue par la collecte.

Chaque élément de contexte doit conserver sa provenance. En son absence, un commentaire vague doit être déclaré inexploitable plutôt que surinterprété.

## Modifications retenues dans le pilote

1. Retrait du sentiment et de l'aspect historiques du prompt enseignant.
2. Encodage contraint des 15 couples famille/listes d'attributs.
3. Conservation de la limite de trois intentions.
4. Règle explicite : un pays, une ville ou une région utilise le type `lieu`.
5. Réalignement déterministe et auditable des citations.
6. Conservation des sorties brutes lorsqu'une correction est appliquée.
7. Résultats et rapports écrits dans des dossiers horodatés, sans écrasement.

## Seuil avant génération massive

Ne pas reprendre les lots de plusieurs milliers d'exemples avant d'obtenir :

- 100 % de JSON parsable après une seule génération ou une relance contrôlée ;
- 100 % de conformité au schéma après normalisation déterministe ;
- 100 % de citations retrouvées exactement dans le texte ;
- au moins 95 % de précision humaine sur les alertes critiques ;
- au moins 85 % d'accord inter-annotateurs sur sentiment, intentions et pertinence ;
- au moins 80 % d'accord sur famille et attribut d'aspect ;
- un test équilibré sur au moins 100 commentaires réels et plusieurs secteurs.

## Format recommandé pour le fine-tuning

Le dataset final devrait séparer :

- l'entrée : commentaire brut et contexte explicitement disponible ;
- la cible : objet JSON V1 validé ;
- les métadonnées : source, version du schéma, modèle enseignant, validation et éventuelles corrections.

Les traces `<think>`, les cinq étapes rédigées et le ChatML imbriqué de l'ancien pipeline ne doivent pas être utilisés comme cible. Le raisonnement utile est représenté par les preuves, les aspects, les intentions et les décisions structurées.

