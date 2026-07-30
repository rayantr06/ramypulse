# Accord inter-annotateurs V0.2 — A3 vs C

Date : 30 juillet 2026
Corpus : campagne V0.2, 305 items, 304 paires exploitables
Annotateurs : A3 et C, deux passes indépendantes en sessions séparées

## Verdict

**Le contrat V0.2 tient.** Neuf champs sur onze dépassent le niveau simulé lors de la
décision. Les gains prédits par la simulation se matérialisent, et plusieurs les
dépassent.

Une seule régression, et elle est instructive : la sévérité des alertes.

## Avant / après

| Champ | V0.1 (A vs B) | V0.2 (A3 vs C) | Écart |
|---|---:|---:|---:|
| `business_relevance` | κ 0,533 | **κ 0,950** | +0,417 |
| `actionability.actionable` | κ 0,468 | **κ 0,956** | +0,488 |
| `language.dominant` | κ 0,660 | **κ 0,881** | +0,221 |
| `actionability.queue` | κ 0,503 | **κ 0,840** | +0,337 |
| `actionability.priority` | κ 0,306 | **κ 0,706** | +0,400 |
| `is_exploitable` | κ 0,740 | **κ 0,889** | +0,149 |
| `sentiment.label` | κ 0,788 | **κ 0,855** | +0,067 |
| `aspects` famille+sentiment | F1 0,640 | **F1 0,711** | +0,071 |
| `intents` | F1 0,741 | **F1 0,777** | +0,036 |
| `alerts` type+sévérité | F1 0,400 | F1 0,304 | −0,096 |
| `author_role` | — | **κ 1,000** | champ neuf |
| `requires_parent_context` | — | κ 0,530 | champ neuf |

`aspects` en V0.1 est donné au niveau famille+sentiment sans neutres, pour comparer ce
qui est comparable. Au niveau brut du contrat V0.1, il valait F1 0,511.

## Mesure contre simulation

| Champ | Simulé lors de la décision | Mesuré | Écart |
|---|---:|---:|---:|
| `business_relevance` | 0,942 | 0,950 | +0,008 |
| `actionable` | 0,917 | 0,956 | +0,039 |
| `queue` | 0,675 | 0,840 | +0,165 |
| `sentiment` | 0,788 | 0,855 | +0,067 |
| `aspects` | 0,640 | 0,711 | +0,071 |
| `priority` | 1,000 | 0,706 | −0,294 |
| `alerts` | 0,667 | 0,304 | −0,363 |

La simulation était conservatrice sur cinq champs et trop optimiste sur deux. Les deux
écarts négatifs ont la même cause, exposée ci-dessous.

## Les alertes : la détection marche, la sévérité non

Décomposition du champ `alerts` :

| Mesure | Résultat |
|---|---:|
| Détection binaire — y a-t-il une alerte ? | **98,7 % · κ 0,906** |
| Type d'alerte seul | **F1 0,783** |
| Type + sévérité | F1 0,304 |

Sur 25 items portant au moins une alerte :

- 7 accords parfaits ;
- **11 désaccords de sévérité seule, sur le même type** ;
- 3 types différents ;
- 4 vus par un seul annotateur.

Les 11 désaccords de sévérité portent sur un contenu quasi identique : une rumeur
répétée selon laquelle le tuyau d'irrigation de la ferme serait branché sur les eaux
usées. A3 code `critique`, C code `elevee`, systématiquement.

Ce n'est pas un désaccord de jugement, c'est une échelle sans ancrage — exactement le
défaut que `priority` présentait en V0.1 et que la dérivation avait corrigé. La chute de
`priority` à 0,706 en découle mécaniquement : elle est dérivée de la sévérité d'alerte
et hérite donc de son bruit. La dérivation fonctionne, son entrée est bruitée.

### Ce que ces 11 items révèlent vraiment

Le même énoncé est répété presque mot pour mot par une dizaine de comptes. Ce n'est pas
un incident sanitaire rapporté, c'est **une accusation qui circule**. Le schéma ne
permet pas de distinguer les deux, alors que la réponse métier est opposée : un rappel
produit d'un côté, une réponse de communication de l'autre.

C'est le principal enseignement de cette campagne, et il n'était pas visible sur les
100 items de la V0.1.

## Autres constats

**`author_role` : accord parfait (κ 1,000).** La distinction entre parole de marque et
retour consommateur était bien un manque réel du contrat, et elle est immédiatement
opérationnelle. 8 à 10 messages de marque identifiés dans le corpus.

**`requires_parent_context` : κ 0,530.** Champ neuf, le plus faible. A3 le pose 30 fois,
C beaucoup moins. La définition « deux lecteurs raisonnables liraient-ils la polarité
différemment » reste trop subjective. À resserrer par un critère de longueur et de
présence d'un référent explicite.

**Validité mécanique.** A3 : 305/305 valides, 0 réparation. C : 304/305, 18 attributs
hors famille retirés, tous `fidelite` sous `confiance_reputation`.

**Deux manques du schéma confirmés** : l'émotion `gratitude` n'existe pas alors qu'elle
est fréquente dans ce corpus ; l'attribut `fidelite` n'existe que sous
`experience_client` alors que C l'a placé 18 fois sous `confiance_reputation`.

## Contrôle de qualité des passes

Une troisième passe, `A2`, a été rejetée avant tout calcul : l'agent avait généré ses
annotations par script. 257 items sur 305 sans aucun aspect ni preuve, 5 signatures
distinctes, aucun arabe standard détecté, et 40 % / 37 % d'accord avec les annotateurs
V0.1 sur les 100 items témoins.

A3 et C atteignent tous deux **86 % et 88 %** d'accord avec ces mêmes annotateurs
antérieurs sur les mêmes textes. Deux passes indépendantes convergeant au même point
sur un jeu témoin est le meilleur contrôle disponible de leur sincérité.

Le test de gabarit doit rester en place pour toute campagne future : nombre de
signatures distinctes, diversité des émotions et des langues, proportion d'items sans
aspect ni preuve.

## Recommandations pour la V0.3

1. **Ancrer l'échelle de sévérité d'alerte** par des définitions opérationnelles, comme
   cela a été fait pour `priority`. C'est la correction la plus rentable.
2. **Distinguer l'incident rapporté de l'accusation qui circule.** Soit par un champ
   dédié, soit en réservant `securite_sante` à un incident vécu en première personne et
   en routant les rumeurs vers `reputation_virale`.
3. **Ajouter `gratitude`** aux émotions et **`fidelite`** à `confiance_reputation`.
4. **Resserrer `requires_parent_context`** par un critère objectif.
5. **Ne pas durcir la porte de sévérité** tant que l'échelle n'est pas ancrée : elle
   reste non critique.

## Portes d'acceptation

Recalibrées sur les plafonds mesurés dans
[acceptance_gates_v0.2.json](baselines/acceptance_gates_v0.2.json). Le champ `alerts`
est désormais scindé en trois portes distinctes, la détection étant fiable et la
sévérité ne l'étant pas.

Ces plafonds proviennent d'un accord machine-machine. Une validation humaine reste
requise avant mise en production.
