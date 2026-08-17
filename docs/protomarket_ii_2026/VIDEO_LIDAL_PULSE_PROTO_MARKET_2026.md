# Vidéos ProtoMarket — LIDAL Pulse

## Positionnement honnête du prototype

La démonstration utilise l’ancienne base locale préparée pour Ramy (`demo-expo-2026`). Elle permet de montrer un parcours fonctionnel de bout en bout sans dépendre du futur SLM ni d’une infrastructure de production.

Pendant la vidéo, présenter les éléments ainsi :

- l’interface, l’API et la base de démonstration sont fonctionnelles ;
- les 200 avis affichés constituent un corpus de démonstration préparé pour valider le produit ;
- le SLM algérien V2 est en cours d’entraînement et ne doit pas être présenté comme déjà déployé ;
- Ramy est un client potentiel ayant autorisé sa mention, pas un client payant déjà en production ;
- le financement demandé servira à industrialiser la collecte, l’IA, l’hébergement algérien et la validation terrain.

## Avant d’enregistrer

1. Démarrer l’API depuis `G:\ramypulse` :

   ```powershell
   python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
   ```

2. Démarrer le frontend dans un second terminal :

   ```powershell
   cd G:\ramypulse\frontend
   npm run dev -- --host 127.0.0.1
   ```

3. Ouvrir `http://127.0.0.1:5173/#/` et vérifier que l’espace affiché est « Ramy · Démo Expo ».
4. Fermer les notifications, terminaux et onglets personnels avant l’enregistrement.
5. Utiliser un affichage 1440 × 900 ou 1920 × 1080 et un zoom navigateur de 100 %.

## Vidéo du prototype — 1 min 45 à 2 min

### 0:00–0:15 — Problème

**Voix :** « Les entreprises algériennes reçoivent des avis en français, en arabe et en daridja sur plusieurs canaux. Ces signaux restent dispersés et difficiles à transformer en décisions rapides. »

**Écran :** logo LIDAL Pulse, puis page « Situation du jour ».

### 0:15–0:40 — Vue décisionnelle

**Voix :** « LIDAL Pulse centralise ces avis, mesure la perception et fait remonter les changements qui nécessitent une vérification humaine. Ici, 200 avis sont synthétisés en un score de perception, une évolution et deux alertes prioritaires. »

**Écran :** montrer 72/100, +5 points, 200 avis et les alertes. Cliquer sur « Voir les preuves » sans modifier le statut d’une alerte.

### 0:40–1:05 — Surveillances métier

**Voix :** « L’entreprise organise sa veille par marque, produit ou concurrent. Elle compare ici YaghurtPlus à LactoDar et suit automatiquement le volume, le score de perception et les aspects comme le goût, le prix ou la disponibilité. »

**Écran :** page « Sujets surveillés », sélectionner successivement LactoDar et YaghurtPlus.

### 1:05–1:30 — Création assistée

**Voix :** « Pour créer une nouvelle surveillance, l’utilisateur décrit simplement son besoin. LIDAL prépare les sources, la zone, les langues et les règles d’alerte ; les paramètres techniques restent modifiables. »

**Écran :** « Créer une surveillance », choisir l’exemple sur les avis du goût, puis « Préparer la surveillance ». S’arrêter à l’écran « Votre surveillance est prête » et ne pas cliquer sur « Créer et lancer » pendant la captation.

### 1:30–1:50 — Comprendre et agir

**Voix :** « Les équipes peuvent ensuite consulter les verbatims multilingues, vérifier les preuves et passer du signal à une action recommandée, toujours avec validation humaine. »

**Écran :** montrer brièvement « Explorer les avis », « Alertes à traiter » puis « Actions recommandées ».

### 1:50–2:00 — Conclusion

**Voix :** « Le prototype valide le parcours Surveiller, Comprendre, Agir. ProtoMarket permettra de l’industrialiser avec le modèle algérien spécialisé, les connecteurs de collecte, l’hébergement et les tests auprès des organisations pilotes. »

## Pitch projet — 3 minutes maximum

### 0:00–0:35 — Besoin

« Chaque jour, les entreprises algériennes reçoivent des milliers d’avis en français, arabe et daridja. Les outils internationaux comprennent mal ce contexte local, tandis que l’analyse manuelle est lente. Les signaux importants — problème de qualité, rupture, campagne mal reçue ou pression concurrentielle — sont détectés trop tard. »

### 0:35–1:15 — Solution

« LIDAL Pulse est une plateforme d’intelligence client qui collecte, structure et analyse ces retours. Elle permet de surveiller une marque, un produit, un concurrent ou une campagne, puis de présenter les alertes, les preuves et les recommandations dans un parcours simple : Surveiller, Comprendre, Agir. Notre différenciation est la compréhension du contexte algérien et la possibilité de déployer des modèles spécialisés, plus petits et maîtrisables. »

### 1:15–1:55 — Preuve actuelle

« Nous avons déjà une application fonctionnelle, une API, une base de démonstration, des vues de veille, d’alertes, d’exploration et de recommandation. Le prototype affiche ici l’analyse de 200 avis et compare une marque à son concurrent. Ramy nous a autorisés à le présenter comme client potentiel pour une expérimentation. En parallèle, le modèle V2 est en cours d’entraînement sur un schéma d’annotation professionnel. »

### 1:55–2:35 — Usage du financement

« Le financement ProtoMarket ne sert pas à refaire une maquette. Il sert à transformer le prototype en bêta testable : connecteurs de données conformes, infrastructure et hébergement, entraînement et inférence du modèle, sécurité multi-tenant, validation des performances et expérimentation auprès d’organisations pilotes. »

### 2:35–3:00 — Impact

« LIDAL Pulse aide les organisations à écouter le marché algérien dans ses langues réelles, à réduire le temps de détection des problèmes et à prendre des décisions fondées sur des preuves. Le premier produit est l’intelligence client ; la technologie et les jeux de données spécialisés pourront ensuite être adaptés à d’autres métiers. »

## Éléments à ne pas montrer ou promettre

- aucune clé API, aucun terminal et aucune donnée personnelle ;
- ne pas dire que les réseaux sociaux sont tous collectés en temps réel si le connecteur concerné n’est pas activé ;
- ne pas prétendre que le SLM V2 produit les résultats actuels ;
- ne pas cliquer sur des actions qui changent le statut des alertes pendant l’enregistrement principal ;
- ne pas présenter les données de démonstration comme des résultats commerciaux réels de Ramy.
