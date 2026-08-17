# Test de rendement — avis Google Maps contre commentaires de page de marque

Date : 30 juillet 2026
Coût total : environ 1,50 USD, 95 appels API

## Question posée

Notre corpus vient de pages de marque, où 41 % des items n'ont aucun aspect et où il
n'existe que 16 événements d'alerte distincts sur 305 items. Les avis Google Maps
sont-ils réellement plus riches, et de combien ?

## Résultat principal

198 avis Maps sur 40 lieux, contre 198 commentaires de page de marque tirés du corpus
existant.

| Indicateur | Avis Maps | Page de marque | Écart |
|---|---:|---:|---:|
| Longueur médiane | **272 car.** | 38 car. | ×7,2 |
| Longueur moyenne | 336,6 car. | 46,0 car. | ×7,3 |
| Items de moins de 30 caractères | **5 %** | 35 % | ÷7 |
| Items portant un marqueur évaluatif | **83 %** | 8 % | ×10 |

Le marqueur évaluatif est un test lexical grossier, appliqué à l'identique aux deux
sources. Il ne remplace pas une annotation, mais l'écart qu'il mesure est symétrique
donc interprétable. **Un facteur 10 ne s'explique pas par l'imprécision de la mesure.**

## Les alertes, blocage n°1 du projet

| Note | Avis | Part |
|---:|---:|---:|
| 1 étoile | 53 | 26,8 % |
| 2 étoiles | 8 | 4,0 % |
| 3 étoiles | 9 | 4,5 % |
| 4 étoiles | 22 | 11,1 % |
| 5 étoiles | 106 | 53,5 % |

**30,8 % des avis sont à 1 ou 2 étoiles**, et ils proviennent de **28 lieux distincts**.

À comparer aux **16 événements d'alerte distincts** que compte l'intégralité de notre
gold de 305 items. Un seul passage de 40 lieux, à 1 dollar, produit davantage
d'événements candidats que tout le corpus construit jusqu'ici.

Les 158 événements nécessaires pour rendre la porte d'alerte statistiquement évaluable
demandent donc environ 220 lieux, soit un ordre de grandeur parfaitement atteignable.

Exemples réels de contenu 1 étoile, tous porteurs d'aspects explicites :

- « c'est une arnaque ce fast food » — fraude, restauration
- « Le pire accueil et service que j'ai eu de ma vie. On a attendu 30 min » — accueil, attente
- « Clinique extrêmement dangereuse, ils voulaient faire une intervention chirurgicale sans faire le… » — **sécurité sanitaire**
- « خدمات ما تشرف… شابون مافي مناشف مافي » — absence de savon et de serviettes, hôtellerie
- « استقبال من الباب يحقرك بالعين ويهدر معاك باستعلاء » — mépris à l'accueil

## Correction d'une erreur de mesure

Le premier passage donnait **93 % de français**, ce qui aurait disqualifié la source :
notre difficulté principale est le darija et l'arabizi.

C'était un artefact de ma requête. Le paramètre `language` de l'API **sélectionne** les
avis selon leur langue :

| Paramètre | Avis renvoyés |
|---|---|
| aucun | anglais |
| `language='fr'` | français |
| `language='ar'` | 5 sur 5 en arabe |

Mesure refaite en interrogeant les deux langues, sur 15 lieux et 150 avis :

| Langue réelle | Part |
|---|---:|
| Latin, français | 49,3 % |
| **Arabe** | **36,7 %** |
| Mixte arabe-latin | 8,7 % |
| **Arabizi** | **5,3 %** |

Près de la moitié du contenu est en écriture arabe ou mixte, et il s'agit bien de darija
naturelle : « البنة ماشاءالله و سرعة », « شابون مافي مناشف مافي ». L'arabizi est présent :
« N3yt nl9a tlf tafi », « Mo3amala top », « Ca fait 3 ans nakol ltem koulyoum ».

## Piège à éviter lors de la collecte réelle

Interroger plusieurs langues renvoie **la même critique deux fois**, une fois dans sa
langue d'origine et une fois traduite par Google. Exemple observé : « Salam alaikoum…
tacos 500/500 » et « السلام عليكم … التاكو 500/500 » sont un seul avis.

La déduplication par texte ne les rattrape pas, puisque les textes diffèrent. Il faut
**conserver uniquement les avis dont `original_language` correspond à la langue
demandée**. L'API expose ce champ.

Sans cette précaution, un corpus de 10 000 avis en contiendrait la moitié en doublons
traduits, et le modèle apprendrait sur des traductions automatiques présentées comme des
avis authentiques.

## Limites

- **5 avis maximum par lieu.** L'API Place Details ne renvoie pas davantage. Le volume
  vient du nombre de lieux, pas de leur popularité.
- **Biais vers les extrêmes.** 53,5 % de 5 étoiles et 26,8 % de 1 étoile : les avis
  Maps sont polarisés. C'est utile pour les alertes, mais la distribution ne reflète pas
  l'opinion moyenne.
- **Conditions d'utilisation.** L'API Places encadre la conservation et la réutilisation
  des avis. Pour ce test d'évaluation, l'usage est limité. Avant d'en faire un corpus
  d'entraînement commercial, ce point doit être tranché.
- **Le marqueur évaluatif est lexical**, donc imparfait. Il indique un ordre de grandeur,
  pas une mesure d'aspects.

## Conclusion

La source est nettement supérieure au corpus actuel sur les trois dimensions qui
bloquaient le projet : densité d'avis, diversité sectorielle, et surtout disponibilité
d'alertes distinctes.

Elle ne remplace pas la collecte sociale : les pages Facebook restent la source de
l'arabizi dense et du sentiment de marque. Les deux sont complémentaires — Maps apporte
l'avis structuré et l'alerte, le social apporte la langue et le rapport à la marque.
