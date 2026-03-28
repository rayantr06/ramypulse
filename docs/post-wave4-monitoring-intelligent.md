# RamyPulse — Piste Post-Wave 4

## Objet
Conserver une réflexion produit/technique pour une future extension de RamyPulse après la fin de la Wave 4.

Le besoin visé n'est pas seulement d'explorer les avis ou de poser des questions via le RAG, mais de mettre en place un système de surveillance intelligent, orienté métier, capable de suivre automatiquement des signaux définis par l'équipe.

## Idée centrale
Ajouter une couche de monitoring intelligent et de notifications au-dessus du socle actuel :
- dashboard ABSA
- explorateur
- chat RAG
- simulation What-If

Cette future brique doit permettre de :
- suivre des dimensions métier plus fines
- détecter automatiquement des dégradations ou anomalies
- remonter des alertes utiles sans attendre une question manuelle

## Exemples de cas à suivre
- baisse du score livraison dans la wilaya d'Oran
- baisse de disponibilité d'un produit donné dans une wilaya donnée
- hausse anormale des plaintes sur l'emballage dans une région
- montée des commentaires négatifs sur un réseau social précis dans une zone précise
- baisse de perception du goût sur une gamme ou un SKU spécifique
- hausse des mentions de rupture pour un parfum ou format particulier

## Ce que cela ajouterait par rapport au système actuel
Aujourd'hui, l'application est surtout :
- un système d'analyse et de visualisation
- un système de question-réponse assisté par RAG
- un système de simulation d'impact

Le monitoring intelligent serait différent :
- le RAG répond à une question posée par l'utilisateur
- le monitoring détecte et pousse une information sans attendre de question

En résumé :
- RAG = interrogation
- monitoring = surveillance + détection + alerte

## Dimensions métier à envisager
Le socle actuel suit surtout :
- aspect
- sentiment
- canal
- timestamp
- source
- confidence

Pour la future extension, il faudra probablement ajouter :
- wilaya
- produit
- gamme
- SKU ou variante
- type de point de vente ou circuit
- zone de livraison
- éventuellement campagne / promotion / distributeur

## Fonctionnalités futures envisagées

### 1. Filtres métier enrichis
- filtre par wilaya
- filtre par produit
- filtre croisé produit × wilaya
- filtre croisé canal × wilaya
- filtre par gamme ou format

### 2. Watchlists métier
Permettre de définir explicitement des éléments à surveiller, par exemple :
- livraison à Alger
- disponibilité du jus citron à Oran
- image de la gamme Premium à Constantine
- emballage sur Facebook dans l'ouest

### 3. Détection d'évolution
Le système devrait pouvoir détecter :
- baisse significative du NSS
- hausse soudaine des mentions négatives
- rupture inhabituelle de disponibilité
- dérive d'un aspect sur une période courte
- changement de perception dans une zone particulière

### 4. Notifications intelligentes
Exemples de messages attendus :
- "Le NSS livraison Oran a diminué de 14 points cette semaine."
- "La disponibilité du produit X à Alger est en baisse sur Google Maps."
- "Les plaintes sur l'emballage augmentent sur Facebook dans l'est."

### 5. Détection de patterns intéressants
Au-delà des règles fixes, le système pourrait aussi détecter :
- anomalies temporelles
- émergence d'un nouveau problème
- concentration géographique d'un signal négatif
- divergence entre canaux sur un même produit

## Hypothèse produit
Cette extension est une bonne idée, car elle apporte une vraie valeur opérationnelle :
- lecture plus rapide des signaux utiles
- surveillance proactive
- priorisation plus métier
- meilleure exploitation des données multi-canales

Elle ne remplace pas le dashboard ni le RAG :
- le dashboard reste l'outil de lecture globale
- le RAG reste l'outil d'interrogation libre
- le monitoring devient l'outil de vigilance et d'alerte

## Pré-requis probables
Avant de l'implémenter proprement, il faudra :
- stabiliser la Wave 4
- fiabiliser la pipeline de données bout en bout
- enrichir le schéma avec les dimensions métier nécessaires
- définir les règles de détection utiles
- clarifier les canaux de notification

## Proposition d'implémentation future
Cette idée pourrait faire l'objet d'une future Wave dédiée, par exemple :
- Wave 5 : Monitoring intelligent et alertes métier

Contenu possible :
- extension du schéma de données
- règles de surveillance configurables
- watchlists sauvegardées
- moteur d'alerting
- centre de notifications dans l'app
- cartes et vues géographiques si la donnée wilaya est disponible

## Décision actuelle
Ne pas implémenter maintenant.

Conserver cette note comme piste officielle à reprendre après finalisation de la Wave 4.
