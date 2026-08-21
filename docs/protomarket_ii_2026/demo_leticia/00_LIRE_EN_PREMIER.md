# LIDAL Pulse — lire en premier

Ce dossier prépare deux captations distinctes :

1. la **vidéo du prototype**, qui montre en deux minutes un parcours produit préparé ;
2. le **pitch de trois minutes**, qui présente le projet, son modèle économique envisagé et l’usage du financement ProtoMarket.

Ne mélangez pas les deux scripts. Commencez par [01_INSTALLATION_WINDOWS.md](01_INSTALLATION_WINDOWS.md), puis répétez le parcours de [02_SCRIPT_VIDEO_PROTOTYPE.md](02_SCRIPT_VIDEO_PROTOTYPE.md) avant d’enregistrer.

## Ce que la démonstration prouve honnêtement

- LIDAL Pulse est un prototype frontend fonctionnel et autonome pour ce parcours.
- Les données et sorties visibles sont des exemples assainis, déterministes et préparés pour la démonstration.
- LIDAL AI est le moteur spécialisé visé ; le SLM algérien est encore en validation.
- Aucune collecte en direct, inférence en direct ou connexion à un système client n’est revendiquée.
- RamyPulse et Alerte IA sont des expériences fondatrices. Ramy peut être présenté comme client potentiel pour une expérimentation, jamais comme client payant déjà déployé.
- L’action reste humaine : vérifier les preuves et le stock avant tout réassort ciblé.

## Parcours à mémoriser

`Facebook → Google Maps → YouTube → Audio autorisé → QR → surveillance de la disponibilité à Oran → preuve SLM préparée → alerte → décision humaine`

Le QR s’ouvre avec **Tester le formulaire** dans un second onglet du même ordinateur. Aucun téléphone ni tunnel public n’est nécessaire.

## Identité officielle locale

Les deux fichiers livrés sous `frontend/client/public/brand/` sont des copies byte-for-byte. Aucun pixel n’a été redimensionné, recadré ou recompressé.

| Source officielle inspectée | Usage retenu | Dimensions | SHA-256 |
| --- | --- | ---: | --- |
| `Logo_fond_black.png` | shell sombre et miniature sur fond sombre → `lidal-mark-dark.png` | 1024 × 1024 | `9361F066F7906E7D161FE25395F551CBDAB5389214C40FCEB34AC570534B61D4` |
| `Logo_retirerbackground.png` | favicon et écran de conclusion → `lidal-mark-transparent.png` | 500 × 500 | `9D1DB48DBC0E4DAA9E110147D1EEBAF09215DAF940F9C1BDE713B9E703A7D160` |
| `Logo LIDAL.png` | inspecté, non copié : mot-symbole complet redondant pour les deux usages demandés | 1024 × 1024 | `41BD0FEBCF69AC9B0687F5D1FC87BBE10DD784D3B2441BFE1375E8949C58FB46` |

Hashes des fichiers livrés :

- `frontend/client/public/brand/lidal-mark-dark.png` : `9361F066F7906E7D161FE25395F551CBDAB5389214C40FCEB34AC570534B61D4` ;
- `frontend/client/public/brand/lidal-mark-transparent.png` : `9D1DB48DBC0E4DAA9E110147D1EEBAF09215DAF940F9C1BDE713B9E703A7D160`.

## Ordre de travail recommandé

1. Installer et lancer la démo.
2. Ouvrir la route de réinitialisation avec `REINITIALISER_DEMO.ps1`.
3. Régler l’écran sur 1920 × 1080 et le navigateur sur 100 %.
4. Fermer les notifications, terminaux, secrets et onglets personnels.
5. Répéter le parcours prototype en entier, y compris le second onglet QR.
6. Enregistrer la vidéo prototype.
7. Enregistrer séparément le pitch de trois minutes.
