# RamyPulse — Modèle d'intégration client et de surveillance des sources

## Statut
Document de réflexion produit/architecture.

Ce document ne décrit pas une décision finale.  
Il sert à cadrer les options de branchement client, de collecte, de surveillance et d'alerting à considérer après stabilisation de la Wave 4.

## Objectif
Répondre à la question suivante :

Comment un système comme RamyPulse se branche-t-il proprement chez un client réel ?

En particulier :
- comment connecter les sources du client
- comment distinguer API officielle, import manuel et scraping
- comment modéliser une watchlist de sources et de signaux métier
- comment faire évoluer le système vers une surveillance intelligente et proactive

## Point de départ
Aujourd'hui, RamyPulse fonctionne surtout comme :
- système d'analyse locale
- dashboard d'exploration
- chat RAG
- simulateur What-If

Le système actuel n'est pas encore un produit complet de collecte continue multi-sources pour des clients branchés en production.

## Question centrale
Faut-il brancher le système :
- par APIs officielles
- par scraping
- par imports fournis par le client
- par une combinaison de ces approches

## Réponse courte
Le modèle le plus solide en entreprise est presque toujours un modèle hybride :
- APIs officielles pour les actifs détenus ou autorisés par le client
- imports batch ou exports pour les données internes
- écoute publique très cadrée pour les sources non directement connectables
- couche métier de normalisation
- couche de watchlists et d'alerting

Le modèle "on scrape tout avec des mots-clés" est rarement le meilleur socle principal.

## Modèles de branchement possibles

### 1. Connexion par APIs officielles
Cas visés :
- pages Facebook du client
- comptes Instagram professionnels du client
- fiches Google Business Profile du client
- chaînes YouTube du client

Avantages :
- plus propre juridiquement et techniquement
- authentification officielle
- meilleure stabilité
- métadonnées plus fiables
- meilleure industrialisation

Limites :
- limité aux actifs possédés ou autorisés
- onboarding plus complexe
- dépend des permissions plateforme
- parfois validation partenaire requise

### 2. Imports fournis par le client
Cas visés :
- exports CRM
- exports SAV
- exports plateformes e-commerce
- fichiers reviews / tickets / incidents
- données logistiques ou commerciales internes

Avantages :
- simple à lancer
- robuste
- utile pour un POC rapide
- bon complément des APIs

Limites :
- pas toujours temps réel
- dépend de la qualité des exports
- schémas variables

### 3. Scraping / collecte publique
Cas visés :
- signaux publics
- sources non ouvertes par API
- veille concurrentielle ou territoriale

Avantages :
- couverture potentiellement large
- utile pour des sources non connectables

Limites :
- risque de fragilité
- risque juridique / conformité
- maintenance élevée
- pagination, anti-bot, quotas, changement de DOM

Conclusion :
le scraping peut exister, mais plutôt comme couche complémentaire et cadrée, pas comme fondation unique.

## Ce que les plateformes offrent en pratique

### Meta / Facebook Pages
Le modèle standard passe par OAuth et les pages gérées par l'utilisateur du client.
En pratique :
- on récupère un user access token
- puis un page access token
- puis on agit sur les pages que l'utilisateur gère

Cela pousse naturellement vers un modèle :
- "sources owned du client"
- pas "surveillance libre de tout Facebook"

### Instagram
Le modèle officiel est centré sur les comptes professionnels.
Selon la documentation Meta/Postman :
- l'API vise les comptes Business et Creator
- elle ne donne pas accès aux comptes consumer classiques
- dans le modèle Facebook Login, il faut lier une Page à un compte Instagram professionnel

Donc, là encore, le schéma naturel est :
- connexion des actifs du client
- pas scraping générique à grande échelle

### Google Business Profile / Google Maps
Le modèle officiel Google Business Profile vise les établissements du client ou de l'organisation autorisée.
Le setup standard comprend :
- demande d'accès API
- activation des APIs associées
- OAuth 2.0
- accès aux données de localisation / reviews de l'organisation autorisée

Ce n'est pas une API généraliste pour aspirer n'importe quelle fiche publique à volonté.

### YouTube
YouTube expose une API publique plus exploitable pour les commentaires, notamment via :
- `commentThreads.list`
- `comments.list`

Cela peut servir pour :
- chaînes du client
- vidéos ciblées
- cas de veille publique plus ouverts que Meta ou GBP

Mais cela reste borné par quota, structure des ressources et permissions associées.

## Modèle recommandé pour RamyPulse

### Socle 1 — Registre de sources
Créer une table ou couche de configuration des sources surveillées, avec par exemple :
- `source_id`
- `platform`
- `source_type`
- `display_name`
- `external_id`
- `url`
- `owner_type`
- `auth_mode`
- `is_active`
- `sync_frequency`
- `last_sync_at`

Exemples de `source_type` :
- facebook_page
- instagram_business_account
- google_business_location
- youtube_channel
- youtube_video
- imported_dataset
- internal_export

### Socle 2 — Catalogue métier
Créer une couche métier distincte des sources :
- produit
- gamme
- SKU
- wilaya
- zone de livraison
- point de vente
- distributeur
- canal

Pourquoi :
- une même source peut parler de plusieurs produits
- une même wilaya peut être couverte par plusieurs sources
- les alertes métier doivent porter sur des entités, pas seulement sur des URLs

### Socle 3 — Watchlists
Permettre de définir explicitement ce qu'on veut suivre.

Exemples :
- disponibilité du jus citron à Alger
- livraison à Oran
- emballage sur Facebook dans l'ouest
- perception du goût gamme Premium à Constantine
- problèmes de fraîcheur sur Google Maps dans une wilaya

Une watchlist devrait pouvoir combiner :
- source(s)
- produit(s)
- wilaya(s)
- aspect(s)
- canal(aux)
- période
- type de métrique

### Socle 4 — Moteur d'alertes
Au-dessus des watchlists, ajouter un moteur de détection.

Exemples de règles :
- NSS baisse de plus de X points
- volume négatif augmente de Y%
- pic inhabituel sur un aspect
- rupture de disponibilité sur une zone
- divergence forte entre canaux

Exemples d'alertes :
- "Le NSS livraison Oran a diminué de 14 points cette semaine."
- "La disponibilité du produit X à Alger baisse sur Google Maps."
- "Les mentions négatives sur l'emballage montent sur Facebook dans l'est."

## Pourquoi ce n'est pas la même chose que le RAG

### RAG
Le RAG répond à une question posée par un utilisateur.

Exemple :
- "Que pensent les clients de l'emballage Ramy ?"

### Monitoring / alerting
Le monitoring détecte et pousse une information sans attendre une question.

Exemple :
- "Le score disponibilité Oran a chuté cette semaine."

Conclusion :
- le RAG = interrogation libre
- le dashboard = lecture globale
- le monitoring = vigilance proactive

Ces 3 briques sont complémentaires.

## Faut-il ajouter seulement des mots-clés ?
Pas idéal comme base principale.

Une logique purement mots-clés crée vite :
- bruit
- ambiguïtés produit
- faux positifs géographiques
- confusion entre marque, gamme et contexte

Les mots-clés restent utiles, mais comme une couche parmi d'autres :
- registre de sources
- mapping entités métier
- règles
- classifieurs
- détection statistique / heuristique

## Options d'onboarding client

### Option A — Onboarding léger
Le client fournit :
- exports CSV / Parquet
- liste de pages / comptes / établissements
- nomenclature produits
- éventuellement mapping wilaya

Avantage :
- rapide pour démarrer

### Option B — Onboarding API officiel
Le client connecte :
- Meta Business / Pages
- Instagram pro
- Google Business Profile
- YouTube

Avantage :
- plus industrialisable
- meilleur futur produit

### Option C — Modèle hybride recommandé
Combiner :
- connexions API officielles
- imports manuels / batch
- quelques flux publics ciblés

C'est le modèle le plus crédible pour une version entreprise.

## Ce qu'il faudrait ajouter au schéma de données
Pour aller vers ce modèle, les colonnes actuelles seront probablement insuffisantes.

Dimensions à envisager :
- `product`
- `product_line`
- `sku`
- `wilaya`
- `delivery_zone`
- `store_type`
- `distributor`
- `source_registry_id`
- `watchlist_id`

Aujourd'hui, le standard projet couvre surtout :
- `text`
- `sentiment_label`
- `channel`
- `aspect`
- `source_url`
- `timestamp`
- `confidence`

Il faudra sans doute enrichir ce modèle, sans casser la compatibilité du cœur actuel.

## Standards entreprise à viser
Si RamyPulse est branché chez un client réel, les standards à viser sont :
- OAuth pour les comptes autorisés
- permissions minimales
- journalisation des synchronisations
- historisation des snapshots
- séparation entre source brute et donnée enrichie
- mapping métier explicite
- système de watchlists configurable
- moteur d'alerting avec seuils et anomalies
- auditabilité des alertes

## Ce qui semble le plus réaliste pour RamyPulse
À ce stade, le chemin le plus réaliste serait :

### Phase 1
- app basée sur fichiers locaux / imports
- dashboard + explorer + RAG + what-if

### Phase 2
- connexion officielle de sources owned
- registre de sources
- catalogue produit / wilaya

### Phase 3
- watchlists métier
- alertes configurables
- détection de patterns intéressants

### Phase 4
- notifications intelligentes
- surveillance proactive multi-dimensionnelle

## Position de travail proposée
Ce document recommande, à titre de réflexion :

- de ne pas centrer RamyPulse sur le scraping seul
- de viser un modèle hybride
- de prévoir une future couche :
  - registre de sources
  - catalogue métier
  - watchlists
  - alerting

## Suite possible après la Wave 4
Si cette direction est retenue plus tard, elle pourrait faire l'objet d'une future Wave dédiée, par exemple :
- Wave 5 — Intégration client, watchlists et monitoring intelligent

## Références officielles
- Google Business Profile APIs : https://developers.google.com/my-business
- Google Business Profile basic setup : https://developers.google.com/my-business/content/basic-setup
- YouTube `commentThreads.list` : https://developers.google.com/youtube/v3/docs/commentThreads/list
- Meta Instagram API Postman collection : https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api
- Meta Facebook Pages token flow Postman request : https://www.postman.com/meta/facebook/request/bqfxwbp/get-access-tokens-of-pages-you-manage

## Note finale
Ce document est volontairement exploratoire.

Il ne fige pas le produit final, mais il capture une réflexion utile :
- comment brancher RamyPulse chez de vrais clients
- comment dépasser le simple dashboard
- comment préparer une couche de surveillance intelligente qui complète le RAG au lieu de le dupliquer
