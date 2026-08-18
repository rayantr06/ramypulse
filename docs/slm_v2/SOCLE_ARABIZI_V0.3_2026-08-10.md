# Socle arabizi V0.3 — annotation et contrôles

**Date** : 2026-08-10 · **Annotateur** : `G1`, `gemini-3-flash-preview` via Vertex AI Express
**Corpus** : 286 items arabizi tirés des splits `dev`/`test` de Mendeley, Hirak, toxicité, NArabizi

## Pourquoi ce socle

L'arabizi est le seul point où l'accord inter-annotateurs ne mesure rien. Sur la
campagne V0.2, il y était **le plus élevé du corpus** (κ 0,919) alors que la validité
y était **la plus basse** : les deux annotateurs se repliaient ensemble sur `neutre`,
56 % contre 41 % ailleurs. Un défaut partagé est invisible à l'accord.

## Résultat

286 items annotés, **aucun échec**, aucune violation de contrainte : zéro alerte en
`espace_public`, zéro `business_relevance: directe`, zéro `lecture_fr` vide.

| Taux de `neutre` | |
|---|---:|
| Passe biaisée (V0.2) | 56 % |
| Passe corrigée et validée (V0.3) | 12 % |
| **Ce socle** | **5 %** |

## Trois signaux, dont deux corrélés

| Signal | Origine |
|---|---|
| Annotation `G1` | lecture + traduction française obligatoire |
| DziriBERT | encodeur préentraîné sur 1,1 M de tweets algériens |
| Étiquette de corpus | Mendeley / Hirak, tenue cachée pendant l'annotation |

**Accord avec les étiquettes cachées : 82,9 %** sur 146 items comparables.

Sur les 77 désaccords entre l'annotateur et DziriBERT, 50 sont arbitrables par
l'étiquette de corpus :

| | |
|---|---:|
| L'annotateur a raison | **38 — 76 %** |
| DziriBERT a raison | 5 — 10 % |
| Ni l'un ni l'autre | 7 — 14 % |

Sur le plus gros bloc — annoté `positif`, prédit `negatif`, n = 25 — l'annotateur
l'emporte 19 à 2.

### Ce chiffre est un plancher, pas une mesure

DziriBERT et les corpus Mendeley/Hirak ne sont **pas indépendants** : même origine
— réseaux sociaux algériens, étiquetage de foule — et même biais négatif. Deux des
cinq cas où DziriBERT « gagne » sont des questions factuelles que l'annotateur avait
correctement classées `neutre` :

> `azi_0255` « hada serwal ak tbi3 fih » — *Est-ce ce pantalon que tu vends ?*
> `azi_0270` « salem mobilis... la cart sim ta3 talib » — *Bonjour Mobilis, la carte SIM étudiant existe-t-elle encore ?*

Le corpus et DziriBERT les étiquettent tous deux `negatif`. L'annotateur l'emporte
donc *malgré* deux signaux corrélés ligués contre lui.

## Erreurs identifiées

Une seule erreur franche sur 146 : `azi_0068`, « khlaset 3lih mal le pauvre hhhhhhhhhh »
annoté `positif`. Les rires ont été lus comme de la joie alors qu'il s'agit de moquerie
sur le malheur d'un tiers.

Cinq des huit inversions de polarité accusent le corpus Hirak, pas l'annotateur —
« Echitta la9wada » (lèche-bottes) y est étiqueté `positif`.

## Point de vigilance

Le neutre penche vers la sur-attribution : 10 items étiquetés `neutre` par le corpus ont
reçu une polarité, contre 7 dans l'autre sens. C'est le défaut inverse de celui corrigé,
et il est léger — la base ne compte que 15 neutres. À surveiller, pas à corriger.

## Ce qui reste : la relecture humaine

L'accord entre modèles ne prouve rien seul. `relecture_humaine/RELECTURE.md` contient
**64 items** — 39 litiges non tranchés et 25 accords **tirés au hasard**, mélangés et non
identifiés. Les accords sont l'élément décisif : ils sont le seul moyen de détecter un
biais que les trois signaux partageraient.

## Coût

286 items en 29 minutes, 8 requêtes en parallèle. `thinkingLevel: low`, retenu après
mesure : sur les trois items de vérité terrain humaine, `low` et le réglage par défaut
font 3/3 chacun, et la réflexion interne pesait 93 % des jetons de sortie. L'étape
`lecture_fr` tient lieu de délibération, avec l'avantage d'être visible.

Le Batch API Vertex — moitié prix, quota séparé — reste inaccessible : il exige un compte
de service et un bucket GCS, la clé Express seule renvoie `403 aiplatform.batchPredictionJobs`.
