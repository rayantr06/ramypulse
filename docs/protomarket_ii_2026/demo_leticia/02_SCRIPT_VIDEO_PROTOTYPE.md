# Script vidéo prototype — 2 minutes maximum

## Règle de vérité

Cette vidéo montre un **prototype préparé**, pas une collecte ou une inférence live. Dites « sortie préparée » et « modèle en validation ». Ne dites jamais « le modèle analyse en direct » ou « nous collectons actuellement tous ces canaux ».

Avant la prise : lancez la démo, réinitialisez-la, passez en 1920 × 1080 à 100 % de zoom et placez le curseur loin des données personnelles.

## Parcours exact en huit scènes

| Temps et scène | Route à afficher | Clic exact | Narration à prononcer | Ne pas cliquer / ne pas montrer |
| --- | --- | --- | --- | --- |
| **0:00–0:12 — 1. Situation** | `http://127.0.0.1:5173/#/` | Aucun. Laisser le titre et la synthèse visibles. | « Les entreprises algériennes reçoivent des avis en français, en arabe et en darija. Dispersés entre plusieurs points de contact, ces signaux restent difficiles à transformer rapidement en décisions. » | Ne pas ouvrir les notifications. Ne pas parler de collecte temps réel. |
| **0:12–0:28 — 2. Origine des signaux** | `/#/` | Aucun. Parcourir visuellement la ligne des canaux de gauche à droite. | « Ce prototype illustre un parcours autorisé et vérifiable : Facebook, Google Maps, YouTube, audio autorisé, puis QR. LIDAL relie ensuite la langue, la preuve, l’aspect et l’alerte à une décision validée par l’équipe. » | Ne pas ouvrir de lien source externe. Ne pas prétendre que ces canaux sont collectés en direct. |
| **0:28–0:43 — 3. Surveillance** | `/#/watchlists` | Dans la navigation, cliquer **Surveillances** ; dans la liste, cliquer **Produits LIDAL** si la fiche n’est pas déjà sélectionnée. | « Ici, la surveillance porte sur les produits LIDAL, avec un scénario central : la disponibilité à Oran. Le périmètre relie les langues, les territoires et les sources préparées pour la démonstration. » | Ne pas cliquer **Créer une surveillance**. Ne pas modifier le périmètre. |
| **0:43–1:03 — 4. Compréhension SLM** | `/#/explorateur` | Cliquer **Explorer**, puis le verbatim commençant par **Ma l9itch le produit fi Oran** pour afficher son panneau. | « Le commentaire en darija arabizi est conservé avec sa preuve exacte. La sortie structurée préparée identifie la disponibilité, le signalement d’incident, une alerte de rupture et une confiance de 91 %. Le SLM spécialisé est encore en validation. » | Ne pas cliquer l’icône **Ouvrir la source**. Ne pas annoncer de latence ou d’inférence live. |
| **1:03–1:23 — 5. QR dans un second onglet** | `/#/listening-points`, puis `/#/feedback/produit-pilote-demo` dans le second onglet | Cliquer **Points d’écoute** → sélectionner **Produit pilote 1 L** si nécessaire → **Tester le formulaire**. Dans le second onglet : **2 étoiles** → remplir **Votre message** avec `Ma l9itch le produit fi Oran.` → cocher le consentement → **Envoyer mon retour**. Montrer **En attente d’analyse**, puis revenir au premier onglet et actualiser. | « Le QR ajoute un point d’écoute direct sans téléphone pendant la démo. Le formulaire s’ouvre localement dans un second onglet. Le retour soumis reste en attente d’analyse et de vérification ; il n’est pas présenté comme une collecte publique en production. » | Ne pas utiliser un tunnel public. Ne pas sélectionner de fichier personnel, démarrer l’audio ou montrer la barre des favoris. |
| **1:23–1:42 — 6. Signal et preuves** | `/#/signals` | Revenir au premier onglet, cliquer **Signaux**, puis **Disponibilité à vérifier à Oran** si nécessaire. Faire défiler jusqu’à **Pourquoi ce signal existe** et **Preuves reliées**. | « Les commentaires concordants en darija, arabe et français forment une alerte localisée : disponibilité à vérifier à Oran. Les preuves restent consultables avant toute décision. » | Ne pas cliquer **Confirmer le signal**, **Ouvrir un dossier**, **Original** ou **Marquer comme faux positif**. |
| **1:42–1:55 — 7. Action humaine** | `/#/actions` | Cliquer **Actions**, puis **Vérifier la disponibilité LIDAL à Oran** si nécessaire. Montrer **Vérifier le stock des points de vente d’Oran** puis **Préparer un réassort ciblé après vérification**. | « LIDAL propose une séquence contrôlée : vérifier d’abord le stock des points de vente, puis préparer un réassort ciblé seulement si la rupture est confirmée. La décision et l’exécution restent humaines. » | Ne pas cliquer **Démarrer**, **Marquer résolue** ou **Préparer un plan**. Ne pas prétendre qu’une action externe a été déclenchée. |
| **1:55–2:00 — 8. Conclusion** | Écran de fin avec `/brand/lidal-mark-transparent.png` | Fondu vers le logo transparent sur un fond uni de la charte. | « LIDAL Pulse : surveiller, comprendre et agir sur des preuves. ProtoMarket doit nous aider à valider puis industrialiser ce parcours. » | Ne pas afficher de terminal, secret, nom personnel ou résultat commercial fictif. |

## Après une prise interrompue

1. Fermez le second onglet du formulaire.
2. Exécutez `REINITIALISER_DEMO.ps1`.
3. Revenez à `/#/`.
4. Recommencez depuis la scène 1 ; ne reprenez pas au milieu avec un état modifié.
