# RamyPulse - Vision Post-Wave 4

## Statut
Document de vision produit et architecture.

Ce document ne valide pas une decision immediate.
Il capture une direction strategique apres la stabilisation de la Wave 4.

## Intention
Faire evoluer RamyPulse d'un systeme d'analyse ABSA + dashboard + RAG vers une plateforme de pilotage marketing et operationnel.

L'objectif n'est plus seulement de repondre a la question :

"Que se passe-t-il dans les avis ?"

Mais aussi :

- "Que faut-il surveiller ?"
- "Qu'est-ce qui change dans le marche ?"
- "Qu'est-ce qui menace la marque ?"
- "Quelles actions recommander ?"
- "Quelle campagne a vraiment eu un effet utile ?"

## Constat
Le produit actuel couvre surtout 4 usages :

- analyser les retours clients
- explorer les signaux par aspect, canal et periode
- poser des questions via RAG
- simuler un impact potentiel via What-If

Ce socle est bon, mais il reste reactif :

- le dashboard montre
- le RAG explique
- le What-If projette

Il manque encore 3 couches a forte valeur business :

- veille proactive
- intelligence marche / concurrence
- mesure et pilotage de campagnes

## Vision cible
RamyPulse doit evoluer vers 5 modules coherents :

1. Listen
- collecte et normalisation multi-sources
- marque, produits, marche, concurrents

2. Understand
- ABSA, tendances, segmentation, comparaison

3. Monitor
- watchlists, alertes, anomalies, signaux faibles

4. Recommend
- suggestions d'actions marketing, produit, SAV, distribution

5. Measure
- suivi d'evenements, campagnes, influenceurs, activations terrain

## Axe 1 - Watchlists et surveillance intelligente

### Pourquoi
Le client n'a pas seulement besoin d'un dashboard global.
Il a besoin de definir ce qui compte pour lui et d'etre prevenu quand cela bouge.

### Exemples de watchlists utiles
- livraison a Bejaia
- disponibilite du jus citron a Alger
- perception du gout sur une nouvelle gamme
- plaintes emballage sur Facebook
- sentiment Google Maps sur une wilaya
- mentions d'un concurrent sur un nouveau produit

### Modele recommande
Une watchlist ne doit pas etre un simple mot-cle.
Elle doit etre un objet metier configurable.

Champs recommandes :
- `watchlist_id`
- `name`
- `description`
- `scope_type`
- `products`
- `competitors`
- `wilayas`
- `channels`
- `aspects`
- `keywords`
- `source_registry_ids`
- `metric_type`
- `baseline_window`
- `alert_threshold`
- `owner`
- `is_active`

### Sorties attendues
- score courant
- variation sur 7 jours / 30 jours
- volume associe
- top signaux explicatifs
- canaux contributifs
- wilayas contributives
- resume LLM optionnel

## Axe 2 - Intelligence marche et concurrence

### Pourquoi
Suivre seulement la marque n'est pas suffisant.
Une entreprise doit comprendre son contexte :

- quels concurrents montent
- quels produits buzzent
- quels themes dominent le marche
- quelles campagnes concurrentes changent la perception

### Ce que le systeme devrait suivre
- la marque cliente
- les concurrents directs
- la categorie produit
- les themes marche
- les nouveautes produit
- les activations media visibles

### Ce que cela change
On passe de :
- "comment va Ramy ?"

A :
- "comment va Ramy par rapport au marche ?"
- "qui gagne du terrain ?"
- "quel signal concurrent doit etre traite maintenant ?"

### KPI utiles
- part de voix
- part de voix positive
- NSS compare marque vs concurrence
- themes emergents
- produits nouveaux les plus cites
- campagnes concurrentes les plus visibles
- vitesse de propagation d'un signal

## Axe 3 - Campagnes, activations et influenceurs

### Pourquoi
Aujourd'hui, une campagne digitale ou un partenariat influenceur est souvent evalue de facon floue.
Il faut isoler l'evenement pour mesurer son effet.

### Objet metier recommande
Introduire un objet `Event` ou `Campaign`.

Champs recommandes :
- `event_id`
- `name`
- `event_type`
- `brand`
- `products`
- `wilayas`
- `channels`
- `start_at`
- `end_at`
- `goal`
- `budget`
- `hashtags`
- `keywords`
- `tracked_accounts`
- `tracked_posts`
- `tracked_urls`
- `creator_profiles`
- `status`

### Exemples
- `Lancement Jus Citron Mars 2026`
- `Sponsoring Amir Ramadan 2026`
- `Activation plage Bejaia`
- `Campagne disponibilite Ouest`

### Mesures attendues
- volume avant / pendant / apres
- evolution du sentiment
- evolution par aspect
- impact par wilaya
- impact par canal
- impact sur la marque
- impact sur le produit cible
- correlation avec ventes si les ventes sont disponibles

### Cas influenceur
Le systeme doit pouvoir suivre :
- le compte de l'influenceur
- les posts / reels / stories suivis
- les hashtags associes
- les commentaires publics
- les reactions et tendances autour de la campagne

Ce n'est pas seulement du social listening.
C'est de la mesure d'activation marketing.

## Axe 4 - Recommandation d'actions

### Pourquoi
Une alerte seule ne suffit pas.
Le client veut une proposition d'action intelligible et exploitable.

### Exemples de recommandations
- renforcer la communication sur la disponibilite dans une wilaya precise
- ouvrir une action SAV sur un probleme emballage recurrent
- lancer une activation locale la ou le produit perd du terrain
- repliquer a un concurrent qui buzze sur un nouveau produit
- travailler avec un profil influenceur plus adapte a une cible donnee

### Architecture recommandee
Le moteur de recommandation ne doit pas etre un simple prompt libre.
Il doit combiner :

- regles metier
- scores et anomalies
- RAG sur donnees internes
- contexte campagne / produit / marche
- LLM puissant pour le raisonnement final

### Schema logique
1. Detection d'un signal
2. Qualification du signal
3. Recuperation du contexte utile
4. Generation de pistes d'action
5. Scoring de confiance / priorite
6. Validation humaine

### Sortie recommandee
Une recommandation doit contenir :
- le probleme observe
- la preuve resumee
- le niveau d'urgence
- les options d'action
- les hypotheses
- les risques
- la confiance

## Attention critique - Correlation n'est pas causalite

### Risque
Le systeme peut facilement sur-interpreter l'effet d'une campagne ou d'un influenceur.

### Ce qu'il faut eviter
- "la campagne a cause +18 points"
- "cet influenceur a genere la hausse des ventes"

### Ce qu'il faut preferer
- "hausse observee pendant la fenetre de campagne"
- "correlation positive entre l'activation et la hausse des mentions positives"
- "effet probable, a confirmer avec donnees ventes et media"

### Regle produit
Le systeme peut recommander et estimer.
Il ne doit pas affirmer une causalite dure sans donnees suffisantes.

## Surfaces produit envisagees

### 1. Market Radar
Vue globale :
- marque
- concurrents
- themes marche
- nouveaux produits
- buzz en cours

### 2. Watch Center
Centre de surveillance :
- watchlists actives
- alertes recentes
- signaux en degradation
- signaux en amelioration

### 3. Campaign Lab
Pilotage des activations :
- creation d'un evenement
- suivi en cours
- comparaison avant / pendant / apres
- rapport final

### 4. Recommendation Desk
Boite a recommandations :
- priorites d'action
- options proposees
- justification
- export rapport

## Architecture logique recommandee

### Couche 1 - Source Registry
Inventaire des sources :
- pages
- comptes
- fiches
- videos
- datasets importes
- comptes influenceurs suivis

### Couche 2 - Entity Resolution
Mapping vers les entites metier :
- marque
- concurrent
- produit
- gamme
- SKU
- wilaya
- point de vente
- zone de livraison
- campagne

### Couche 3 - Signal Engine
Calcule :
- NSS
- volumes
- variations
- anomalies
- evenements emergents

### Couche 4 - Retrieval Context Layer
Preparer le contexte pour le RAG et les recommandations :
- extraits source
- top preuves
- signaux recents
- historique
- contexte campagne

### Couche 5 - Recommendation Layer
Fusion :
- regles
- analytics
- retrieval
- LLM

## Enrichissements de schema a prevoir
Le schema actuel est trop court pour cette vision.
Il faudra probablement ajouter, sans casser le coeur existant :

- `brand`
- `competitor`
- `product`
- `product_line`
- `sku`
- `wilaya`
- `delivery_zone`
- `store_type`
- `campaign_id`
- `event_id`
- `creator_id`
- `source_registry_id`
- `watchlist_id`
- `market_segment`

## Notifications et delivery
Le systeme doit pouvoir sortir l'information de plusieurs facons :

- centre de notifications dans l'app
- digest quotidien / hebdomadaire
- alertes email
- webhook
- export rapport

Il faut distinguer :
- alertes critiques
- signaux faibles
- recap analytique

## Gouvernance et garde-fous

### Risques techniques
- faux positifs
- bruit lie aux mots-cles
- confusion de produits
- duplication de sources
- attribution abusive

### Risques produit
- trop d'alertes
- recommandations trop generiques
- manque de confiance si le systeme sur-promet

### Garde-fous recommandes
- validation humaine des recommandations critiques
- score de confiance explicite
- tracabilite des preuves
- possibilite de desactiver une watchlist
- seuils ajustables

## Roadmap recommandee

### Phase A - Extension de schema et watchlists
- ajouter produit / wilaya / concurrent / campagne
- definir le registre de sources
- creer les watchlists configurables

### Phase B - Alerting intelligent
- moteur de regles
- detection statistique simple
- centre de notifications

### Phase C - Marche et concurrence
- suivi des concurrents
- part de voix
- radar marche

### Phase D - Campaign Intelligence
- creation d'evenements
- suivi d'activation
- analyse avant / pendant / apres

### Phase E - Recommendation Engine
- recommandations structurees
- synthese LLM
- rapports fin de campagne

## Position recommandee
Cette direction est bonne.
Elle donne au produit une vraie trajectoire entreprise.

Le bon ordre n'est pas :
- tout faire tout de suite

Le bon ordre est :
- stabiliser le socle
- ajouter les dimensions metier
- industrialiser la surveillance
- puis ajouter la recommandation et la mesure d'impact

## Conclusion
La prochaine grande evolution logique de RamyPulse n'est pas seulement "plus de dashboards".

C'est la construction d'un systeme qui :
- surveille la marque
- surveille le marche
- mesure les activations
- recommande des actions
- aide le client a arbitrer son budget et ses priorites

Ce positionnement est plus fort qu'un simple outil d'analyse.
Il rapproche RamyPulse d'une plateforme d'intelligence marketing actionnable.
