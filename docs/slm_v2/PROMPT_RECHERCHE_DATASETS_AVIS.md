# Prompt de recherche — datasets d'avis géolocalisés exploitables pour l'Algérie

À donner tel quel à un agent de recherche.

---

## Mission

Trouver des jeux de données **publics et téléchargeables** d'avis sur des lieux ou des
commerces, contenant de l'**Algérie** — soit directement, soit dans un jeu mondial
filtrable par pays.

Contexte : je construis un corpus d'entraînement pour un modèle d'analyse de commentaires
consommateurs en Algérie (français, arabe, darija, arabizi). J'ai besoin d'avis
**évaluatifs et récents**, avec si possible une note et une catégorie de lieu.

## Ce que j'ai déjà vérifié — ne pas refaire

| Piste | Résultat vérifié |
|---|---|
| Recherche HuggingFace « reviews », « maps », « arabic », 150 datasets vus | Rien pour l'Algérie. Seulement `opdullah/turkish-google-maps-reviews` et `Musaed1/kudu-google-maps-reviews` (chaîne saoudienne) |
| **Google Local 2021** (UCSD / McAuley), 666 M d'avis | **États-Unis uniquement** |
| **Google Local 2018** (UCSD / McAuley), 11,4 M d'avis | International, mais **0,056 % d'Algérie** mesuré sur 42 835 lieux, soit ~1 680 lieux. Données de 2010-2018, majoritairement mosquées, écoles, hôpitaux. Fichiers : places 290 Mo, reviews 1,4 Go |
| **API Google Places officielle** | Fonctionne, mais **5 avis maximum par lieu**, ~0,017 $ par lieu |
| **Apify `compass/Google-Maps-Reviews-Scraper`** | Tous les avis d'un lieu, 0,0006 $ par avis, mais **scraping contraire aux CGU de Google** |

Inutile donc de reproposer Google Local UCSD, l'API Places ou Apify : je les connais.

## Ce que je cherche vraiment

Par ordre de priorité :

1. **Un dump récent (2022-2026) d'avis Google Maps** couvrant plusieurs pays, filtrable
   par pays — l'équivalent du Google Local UCSD mais à jour et international.
2. **Un dataset MENA, Afrique du Nord, monde arabe ou africain** d'avis de lieux.
3. **Un dataset spécifiquement algérien** d'avis : restaurants, cliniques, hôtels,
   commerces, services.
4. **Des plateformes autres que Google** ayant des avis sur l'Algérie et dont les données
   sont partagées : TripAdvisor, Booking, Foursquare, Yelp, Zomato, Trustpilot, Jumia,
   Ouedkniss, ou tout équivalent local algérien.
5. **Des articles de recherche** sur l'analyse d'avis en dialecte arabe ou maghrébin
   ayant publié leurs données.

## Où chercher

- Hugging Face Datasets, Kaggle, Zenodo, Mendeley Data, Figshare, Dataverse
- GitHub — dépôts de scraping partageant leurs résultats, pas seulement le code
- Google Dataset Search
- ACL Anthology, arXiv, ResearchGate — chercher les liens de données dans les articles
  sur l'ABSA arabe, le sentiment dialectal, les avis multilingues
- Common Crawl et jeux dérivés — un sous-ensemble d'avis en aurait-il été extrait
- Awesome-lists sur les datasets NLP arabes
- Places API alternatives publiant des échantillons gratuits : Outscraper, SerpApi,
  Bright Data, Foursquare Places

## Pour chaque piste, réponds impérativement

1. **Nom et URL exacte de téléchargement.** Pas la page projet : le lien du fichier.
2. **A-t-il vraiment de l'Algérie ?** Un chiffre, pas une supposition. Si tu ne peux pas
   le vérifier, dis « non vérifié » — ne devine pas.
3. **Volume** : nombre d'avis, taille du fichier.
4. **Période couverte.** Un dataset antérieur à 2020 m'intéresse peu.
5. **Licence exacte**, et si l'usage **commercial** est permis. « Public sur GitHub » ne
   veut pas dire « autorisé ».
6. **Champs disponibles** : texte, note, catégorie du lieu, date, langue, pays.
7. **Langues présentes**, en particulier arabe et arabizi (arabe en caractères latins
   avec chiffres : `3` pour ع, `7` pour ح, `9` pour ق).
8. **Données personnelles** : le jeu contient-il des noms d'auteurs ou des identifiants ?

## Pièges à éviter — je suis tombé dedans

- **Faux positifs de recherche textuelle.** Chercher « Oran » ramène « Rist**oran**te » et
  « Rest**oran** ». Chercher `رامي` ramène « ح**رامي**ة » (voleurs). Vérifie sur un champ
  pays structuré, pas par sous-chaîne dans du texte libre.
- **Doublons par traduction.** L'API Google renvoie le même avis en plusieurs langues.
  Vérifie si un dataset contient des traductions présentées comme des avis distincts.
- **Licence déclarée contre licence réelle.** Un dataset scrapé et republié en CC-BY ne
  purge pas les droits de la source. Signale le doute plutôt que de le taire.
- **Ne présente pas une extrapolation comme une mesure.** Si tu estimes, dis-le.

## Livrable attendu

Un tableau classé par utilité réelle pour l'Algérie, suivi d'une recommandation courte :
**quelle piste vaut la peine d'être téléchargée en premier, et pourquoi**.

Si aucune piste sérieuse n'existe, dis-le clairement. Une réponse « il n'y a rien de
mieux que ce que tu as déjà » est un résultat utile — inventer une piste faible pour
avoir l'air productif ne l'est pas.
