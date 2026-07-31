# Prompt de recherche — comment récupérer des avis Google Maps à grande échelle

À donner tel quel à un agent de recherche.

---

## Mission

Trouver **toutes les façons d'obtenir des avis Google Maps en volume** : jeux de données
déjà constitués, fournisseurs commerciaux, API, outils open source, ou toute autre voie.

La question porte sur **la méthode d'extraction**, pas sur un pays. L'application finale
est l'Algérie, donc à volume et coût comparables je privilégierai ce qui couvre bien
l'Afrique du Nord et le monde arabe — mais une solution mondiale performante m'intéresse
même sans garantie sur l'Algérie.

Usage prévu : constituer un corpus d'entraînement pour un modèle d'analyse d'avis
consommateurs. Il me faut donc le **texte** des avis, pas seulement des notes agrégées.

## Ce que j'ai déjà vérifié — ne pas reproposer

| Piste | Résultat mesuré |
|---|---|
| **API Google Places officielle** | Fonctionne, mais plafond dur de **5 avis par lieu**, ~0,017 $ par lieu. Le paramètre `language` sélectionne la langue et renvoie le même avis traduit, donc en doublon |
| **Apify `compass/Google-Maps-Reviews-Scraper`** | Tous les avis d'un lieu, **0,0006 $ par avis**, ~50 000 utilisateurs. Mais c'est du scraping, contraire aux CGU de Google |
| **Google Local 2021** (UCSD / McAuley), 666 M d'avis | **États-Unis uniquement** |
| **Google Local 2018** (UCSD / McAuley), 11,4 M d'avis | International, mais données 2010-2018. Fichiers : lieux 290 Mo, avis 1,4 Go |
| Hugging Face, ~150 datasets d'avis parcourus | Rien de mondial et récent. Seulement du turc et une chaîne saoudienne |

## Questions précises auxquelles je veux une réponse

1. **La Places API (New) de Google lève-t-elle la limite des 5 avis ?** Existe-t-il un
   endpoint, un quota payant, un partenariat ou un programme entreprise donnant accès à
   davantage d'avis **légalement** ? C'est la question la plus importante.
2. **Quels fournisseurs commerciaux vendent des avis Google Maps**, et à quel prix réel
   par millier ? Comparer au minimum Outscraper, SerpApi, DataForSEO, Bright Data,
   Oxylabs, ScrapingBee, Zenserp, et tout autre acteur pertinent. Certains proposent des
   **exports en masse** plutôt que du scraping à la demande — c'est ce qui m'intéresse le
   plus.
3. **Existe-t-il des dumps récents (2022-2026)**, académiques ou commerciaux, d'avis
   Google Maps couvrant plusieurs pays ?
4. **Quels scrapers open source** sont maintenus et fonctionnent encore ? Donner le
   dépôt, sa dernière activité, et s'il gère la pagination au-delà des premiers avis.
5. **Quelles sources alternatives** ont des avis en volume et des données plus ouvertes :
   Foursquare, Overture Maps, OpenStreetMap, TripAdvisor, Booking, Trustpilot, Yelp
   Fusion, Zomato ? Préciser lesquelles exposent réellement du **texte d'avis**, et non
   seulement des points d'intérêt.

## Sur la légalité — traiter sérieusement, pas en note de bas de page

Le produit final est **commercial**. Pour chaque piste, indiquer :

- ce que disent les CGU de la source sur l'extraction et la réutilisation ;
- si le fournisseur assume contractuellement le risque juridique ou le reporte sur son
  client ;
- si les avis peuvent servir à **entraîner un modèle**, ce qui est plus engageant qu'un
  simple affichage ;
- l'existence de jurisprudence ou de litiges connus.

Une piste illégale mais performante m'intéresse quand même : je veux la connaître **et
savoir qu'elle est illégale**. Ne pas la cacher, ne pas la maquiller.

## Pour chaque piste, réponds impérativement

1. Nom et **URL exacte** : lien de téléchargement ou page tarifaire, pas une page d'accueil.
2. **Volume accessible** et limite par lieu, s'il y en a une.
3. **Coût réel** pour 10 000 avis, et pour 1 million.
4. **Couverture géographique**, avec un chiffre si disponible.
5. **Champs fournis** : texte, note, catégorie, date, langue, réponse du gérant.
6. **Statut juridique**, selon la section ci-dessus.
7. **Données personnelles** : noms d'auteurs, photos, identifiants sont-ils inclus ?
8. **Fraîcheur** : à quand remontent les données les plus récentes ?

## Pièges rencontrés, à ne pas répéter

- **Doublons par traduction.** Google renvoie le même avis dans plusieurs langues. Une
  déduplication par texte ne les voit pas. Vérifier si un fournisseur livre des
  traductions présentées comme des avis distincts.
- **Faux positifs de recherche textuelle.** Chercher un mot-clé dans du texte libre donne
  des taux d'erreur énormes — 87 % dans mon cas. S'appuyer sur des champs structurés.
- **Licence déclarée contre licence réelle.** Un dataset scrapé puis republié en CC-BY ne
  purge pas les droits de la source.
- **Ne pas confondre estimation et mesure.** Si un chiffre est extrapolé, le dire.

## Livrable

Un tableau comparatif classé par **rapport volume / coût / risque juridique**, suivi de
trois recommandations distinctes :

- la meilleure option **strictement légale** ;
- la meilleure option **au meilleur rapport coût-volume**, risque assumé et nommé ;
- la meilleure option **gratuite**, s'il en existe une.

Si la réponse est « rien ne bat l'API officielle légalement, et Apify sinon », dis-le
franchement. Une conclusion négative documentée vaut mieux qu'une liste de pistes faibles
présentée pour paraître productif.
