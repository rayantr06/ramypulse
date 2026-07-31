# Stratégie de sourcing — trouver les vrais avis

Date : 30 juillet 2026

## Le constat qui motive ce document

Le corpus actuel vient de pages de marque. Sur ces pages, le rituel social produit
surtout des participations à concours, des tags d'amis, des salutations et des formules
religieuses. La densité d'avis y est faible : 41 % des items n'ont aucun aspect, et
16 événements d'alerte distincts seulement sur 305 items.

Le problème n'est pas la quantité de commentaires disponibles. C'est que **nous
collectons aux endroits où les gens ne donnent pas leur avis**.

L'idée directrice, proposée par le propriétaire du projet : cibler les contextes où le
rituel social produit *naturellement* un avis argumenté. Ce document la développe et la
classe par rendement.

---

## Source 1 — Avis Google Maps

**C'est la source la plus rentable, et de loin.**

Un avis Google Maps résout par construction ce que nous peinons à obtenir ailleurs :

| Problème actuel | Ce que l'avis Maps apporte |
|---|---|
| Identifier l'entité surveillée | Un lieu **est** une organisation. Scope `organisation` automatique. |
| Deviner le secteur | La catégorie du lieu le donne : restaurant, clinique, garage, hôtel, agence bancaire, pharmacie. |
| Trouver des aspects | Un avis est évaluatif par nature : service, prix, hygiène, attente, accueil. |
| Trouver des alertes | Les avis 1 étoile concentrent intoxications, hygiène, arnaques, refus de garantie. |
| Contrôler l'annotation | **La note en étoiles est une étiquette faible gratuite.** |

Ce dernier point mérite d'être souligné. Nous avons dû fabriquer des témoins à la main
pour détecter la dérive des annotateurs. Avec Maps, chaque item porte une note de 1 à 5
qui permet de repérer automatiquement toute annotation aberrante — un avis 1 étoile
codé `positif` est un signal d'erreur, à l'échelle de milliers d'items.

Cela résout aussi le défaut qui a plombé toutes mes tentatives d'extraction : chercher
des marques par mots-clés dans du texte libre m'a donné **87 % de faux positifs** au
premier essai, encore 60 % au second. Ici, aucune devinette.

**État technique.** Le collecteur existe déjà :
[`google_maps_reviews.py`](../../core/watch_runs/collectors/google_maps_reviews.py), basé
sur la bibliothèque officielle `googlemaps`. Ce n'est pas du scraping.

**À vérifier avant usage** : les conditions de l'API Places encadrent la conservation et
la réutilisation des avis. Ce point doit être tranché avant toute constitution de corpus
d'entraînement, pas après.

---

## Source 2 — Groupes et pages de protection du consommateur

**C'est là que vivent les alertes.**

Le blocage n°1 du projet est que les alertes ne sont pas évaluables : 16 événements
distincts, dont un cluster de 10 messages sur une même rumeur. Les pages de protection
du consommateur sont l'inverse exact — chaque publication *est* un signalement.

`APOCE Protection Consommateur` figure **déjà** dans
[`targets.yaml`](../../scraping/targets.yaml) et n'a jamais été collectée.

Types d'alerte que cette source exerce naturellement : produits périmés ou avariés,
arnaques et fausses promotions, non-conformité à la description, refus de garantie,
manquements d'hygiène, litiges de facturation.

C'est la source la plus directe pour passer de 16 à plusieurs dizaines d'événements
distincts.

---

## Source 3 — Fils « demande d'avis » dans les groupes spécialisés

**Ce n'est pas une source de plus, c'est une forme de donnée différente.**

Un fil de demande d'avis a une structure que nous n'avons jamais traitée :

```
Post parent : « je cherche une machine à laver à moins de 50 000 DA, wach tanseho ? »
  Réponse 1 : « Condor, mais le SAV est lent »
  Réponse 2 : « Brandt khir, plus cher mais dure »
  Réponse 3 : « ma tchrich Condor, khsara »
```

Trois propriétés qu'aucune autre source ne donne :

1. **Comparatif.** Plusieurs marques évaluées dans le même contexte, avec un besoin
   explicite. C'est de la veille concurrentielle brute.
2. **Argumenté.** Une réponse à une demande d'avis contient presque toujours un motif,
   donc un aspect.
3. **Le scope `secteur` prend enfin son sens.** Ce scope est défini dans le schéma V0.3
   mais n'a **jamais été testé**, faute de données correspondantes. Un fil de demande
   d'avis est exactement une veille sectorielle : la cible n'est pas une marque, c'est
   une catégorie de produit.

**Prérequis technique bloquant.** Le collecteur Facebook capture `postUrl` mais **pas le
texte du post** ([facebook_apify.py:96](../../core/watch_runs/collectors/facebook_apify.py:96)).
Or ici le post parent *est* la question : sans lui, les réponses sont incompréhensibles.

Ce même manque explique le champ `requires_parent_context`, qui plafonne à κ 0,530 et
qu'aucune règle mécanique n'a pu reproduire. **Capturer le texte du post résout les deux
problèmes d'un coup.**

---

## Source 4 — Publications sponsorisées d'influenceurs

Les commentaires sous une publicité d'influenceur se scindent entre adhésion et
scepticisme. Cette source apporte ce qu'aucune autre ne donne :

- des signaux de **défiance** : « ils sont payés pour dire ça », « publicité mensongère » ;
- du **sarcasme** et du sentiment `mixte`, les catégories les plus rares de notre gold ;
- la famille `confiance_reputation`, peu couverte ;
- une **forte densité d'arabizi**, l'audience étant plus jeune — ce qui alimente
  directement la langue où nous avons identifié le biais le plus grave.

---

## Source 5 — Fils d'incident télécom et service public

Quand un opérateur ou un service public subit une panne, la section commentaires se
remplit en quelques heures de signalements localisés.

Cette source produit du `rupture_service` daté et géolocalisé, mais surtout elle
fournit **le cas d'école dont le schéma a besoin** : une même alerte répétée par des
dizaines de comptes en un temps court. C'est exactement la distinction que la décision
D13 introduit sans avoir pu la valider — incident rapporté contre accusation qui
circule — et le signal d'agrégat de D11, qui escalade la criticité sur la répétition.

---

## Classement par rendement

| Source | Résout | Effort | Priorité |
|---|---|---|---|
| Avis Google Maps | secteurs, aspects, alertes, étiquette faible | collecteur existant, ToS à vérifier | **1** |
| Protection du consommateur | alertes diversifiées | cible déjà listée | **2** |
| Fils de demande d'avis | secteurs, comparatif, scope `secteur` | capture du post parent requise | **3** |
| Influenceurs sponsorisés | défiance, sarcasme, arabizi | ciblage manuel des comptes | 4 |
| Incidents télécom | `rupture_service`, validation de D11 et D13 | veille événementielle | 5 |

---

## Points à trancher avant de collecter

1. **Conditions d'utilisation de l'API Places** sur la conservation et la réutilisation
   des avis, pour un usage d'entraînement commercial.
2. **Groupes privés : exclus.** Seules les pages et groupes publics sont envisageables.
3. **Données personnelles.** Les commentaires contiennent des noms de personnes réelles.
   Le pipeline actuel supprime URL, e-mails, téléphones et identifiants `@`, mais **pas
   les noms propres en clair**. Un corpus construit sur ces sources en contiendra
   davantage, pas moins. La pseudonymisation doit être décidée avant la collecte.
4. **Attribution** des corpus publics déjà intégrés, tous en CC-BY-4.0.

## Prochaine étape concrète

Capturer le texte du post parent dans le collecteur Facebook. C'est une modification
courte, elle débloque les fils de demande d'avis, et elle corrige le champ le plus faible
du contrat d'annotation.

Puis un test de rendement sur un échantillon : 200 avis Google Maps contre 200
commentaires de page de marque, en mesurant sur chacun la densité d'aspects, le taux
d'alertes et la part d'items exploitables. Cela donnera un chiffre à opposer aux 41 %
d'items sans aspect du corpus actuel, au lieu d'une intuition.
