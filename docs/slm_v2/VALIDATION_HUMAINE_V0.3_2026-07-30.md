# Validation humaine du gold V0.3

Date : 30 juillet 2026
Relecteur : propriétaire du projet
Échantillon : 60 items, 30 accords A3=C et 30 désaccords, mélangés et présentés
à l'identique sans indication du groupe

## Résultat

| Groupe | n | correcte | nuance | incorrecte | acceptable |
|---|---:|---:|---:|---:|---:|
| Accord A3 = C | 30 | 20 | 7 | 3 | **90 %** |
| Désaccord | 30 | 25 | 4 | 1 | 97 % |

**Pas de biais partagé au niveau global.** Le groupe « accord » dépasse le seuil de
85 % fixé avant la relecture. L'accord inter-annotateurs est donc un indicateur de
qualité crédible à l'échelle du corpus — c'est la validation qui manquait à toute la
démarche, puisque deux LLM peuvent se tromper ensemble sans que la mesure d'accord le
voie jamais.

Les désaccords obtiennent un score **supérieur** aux accords. Cela signifie que sur ces
items, les deux lectures étaient le plus souvent défendables : ce sont de vraies
ambiguïtés, pas des erreurs.

## Mais un angle mort localisé, et il est grave

Les cinq corrections signalées sont **toutes** dans le groupe accord. Trois des quatre
erreurs franches portent sur des commentaires en **arabizi**, tous codés
`neutre / aucun aspect` par les deux annotateurs :

| Item | Contenu | A3 et C | Correct |
|---|---|---|---|
| `v02_0111` | déclaration d'affection explicite avec emojis | neutre | positif |
| `v02_0215` | insulte directe adressée à une personne | neutre | négatif |
| `v02_0120` | contenu sexuel explicite visant une personne nommée | neutre, aucune alerte | harcèlement |
| `v02_0212` | formule d'espoir religieuse (arabe) | positif | neutre |

### Le biais est systématique et mesurable

| | Arabizi | Autres langues | Écart |
|---|---:|---:|---:|
| Sentiment `neutre` | 54 % | 41 % | **+13 pts** |
| Aucun aspect | 56 % | 41 % | **+14 pts** |

### Et il est invisible à la mesure d'accord

| Langue | n | Sentiment κ | Aspects F1 | % neutre |
|---|---:|---:|---:|---:|
| **darija_arabizi** | 41 | **0,919** | 0,762 | 56 % |
| darija_arabe | 128 | 0,869 | 0,774 | 34 % |
| arabe_msa | 92 | 0,786 | 0,640 | 71 % |
| francais | 43 | 0,748 | 0,575 | 28 % |

**Sur l'arabizi, l'accord est le plus élevé du corpus, et la validité la plus basse.**
Les deux annotateurs convergent parce qu'ils appliquent le même repli — `neutre`,
aucun aspect — pas parce qu'ils lisent correctement. L'accord y mesure une convention
partagée.

C'est la démonstration la plus nette possible que l'accord inter-annotateurs ne peut
pas servir seul de critère de qualité, et que la relecture humaine doit rester dans la
boucle.

### Conséquence directe pour l'entraînement

Le corpus arabizi a été délibérément enrichi — 43 items contre 2 en V0.1 — parce que
c'est la langue la plus spécifique au marché algérien. Entraîner sur ce gold en l'état
apprendrait au modèle à répondre `neutre` sur l'arabizi **avec une confiance élevée**,
puisque les deux annotateurs y sont d'accord. Le défaut serait amplifié, pas corrigé.

## Angle mort de sécurité

`harcelement_discrimination` : **0 alerte posée sur 305 items**, par l'un comme par
l'autre annotateur.

Un balayage par indicateurs lexicaux identifie 2 items candidats. Les deux sont en
arabizi, tous deux codés `neutre` et `non exploitable`, **aucun des deux ne déclenche
d'alerte**. Taux de détection : 0 sur 2.

Le volume est faible et ne permet pas de conclusion statistique, mais la catégorie est
sensible et le taux de manque est total. Un système de veille qui classe un contenu
sexuel ciblant une personne nommée en « non exploitable, neutre » est défaillant sur un
point qui engage la responsabilité du client.

## Décisions

1. **Les plafonds mesurés restent valables au niveau global** mais sont **optimistes
   sur l'arabizi**. Une note est ajoutée aux portes.
2. **Ajout de portes par langue** : le modèle devra être évalué séparément sur
   l'arabizi, où l'accord ne peut pas servir de plafond.
3. **`harcelement_discrimination` devient un point de contrôle obligatoire** de toute
   campagne : si zéro alerte de ce type est posée, la campagne signale explicitement
   que la catégorie n'a pas été exercée.
4. **La relecture humaine devient permanente** : tout gold futur inclut un échantillon
   d'accords tiré au hasard, sans quoi ce type de défaut reste indétectable.
5. **Le gold V0.3 n'est pas utilisable tel quel pour l'entraînement** sur la partie
   arabizi. Ces 41 items doivent être réannotés avec une consigne renforcée avant
   d'entrer dans un jeu d'entraînement.

## Ce que la relecture confirme aussi

Sur 60 items, 45 sont jugés pleinement corrects et 11 acceptables avec nuance. Le
contrat V0.3, sa validité mécanique et sa cohérence tiennent. Le problème identifié est
circonscrit à une langue et à une catégorie d'alerte, pas au schéma.
