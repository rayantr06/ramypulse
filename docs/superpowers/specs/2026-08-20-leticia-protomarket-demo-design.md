# LIDAL Pulse — démonstration autonome pour Leticia

**Date :** 20 août 2026
**Statut :** conception approuvée
**Branche cible :** `codex/lidal-pulse-leticia-demo`

## 1. Objectif

Livrer à Leticia une version de LIDAL Pulse fiable, reproductible et adaptée au tournage des deux vidéos ProtoMarket :

1. une démonstration visuelle du prototype ;
2. un pitch projet de trois minutes maximum.

Leticia doit pouvoir cloner la branche, exécuter une commande Windows, suivre un parcours préparé et filmer sans clé API, sans accès aux données privées, sans modèle distant et sans dépendance à un backend de production.

## 2. Critères de réussite

- L'application démarre sur Windows avec un script PowerShell unique après installation.
- Le parcours principal reste déterministe après chaque réinitialisation.
- Les écrans sont complets et lisibles en 1920 × 1080 à 100 % de zoom.
- Le jury comprend l'enchaînement : sources → surveillance → analyse SLM → preuve → alerte → décision humaine.
- Le canal QR est démontré sans téléphone : le formulaire public s'ouvre dans un second onglet sur le même ordinateur.
- Les exemples sont multilingues, cohérents et proches du contrat d'annotation utilisé pour l'entraînement.
- Aucun secret, corpus complet, identifiant personnel ou résultat commercial fictif n'est publié.
- Les affirmations distinguent clairement le prototype fonctionnel du SLM encore en validation.

## 3. Approche retenue

La démonstration sera **frontend-only et autonome**.

Le frontend Vite embarquera un jeu de données assaini et déterministe. Les interactions de tournage seront conservées dans `localStorage` uniquement. Aucun service Python, aucune base distante et aucune API externe ne seront nécessaires au parcours filmé.

Cette approche est préférée au lancement de la pile complète parce qu'elle réduit les risques de port occupé, de configuration Python, d'authentification, de réseau, de quota fournisseur et de panne pendant l'enregistrement.

La pile complète FastAPI/V3 reste hors du chemin de tournage. Elle n'est ni supprimée ni présentée comme remplacée.

## 4. Architecture de la démonstration

### 4.1 Surfaces produit

Le parcours utilisera les surfaces V3 existantes et le module de points d'écoute :

- Aujourd'hui : vue synthétique ;
- Surveillances : cible, canaux et règles ;
- Explorer : avis multilingues et analyse structurée ;
- Signaux : alerte, explication et commentaires sources ;
- Points d'écoute : création et gestion des QR ;
- Formulaire public : retour texte, note, audio ou photo selon la configuration ;
- Actions : décision proposée et validation humaine.

### 4.2 État local

Un dépôt local unique gérera :

- les points d'écoute de démonstration ;
- les scans simulés ;
- les retours soumis ;
- l'état de progression du parcours ;
- la réinitialisation complète.

Les identifiants et jetons publics de démonstration seront fixes afin que les URL restent identiques d'un lancement à l'autre.

### 4.3 Parcours QR fiable

Le QR affiché pointera vers une route de la même application, par exemple :

```text
http://127.0.0.1:5173/#/feedback/produit-pilote-demo
```

Pendant le tournage, Leticia utilisera le bouton « Tester le formulaire ». La route s'ouvrira dans un second onglet. Après l'envoi d'un retour préparé, elle reviendra au premier onglet et verra le retour rattaché au point d'écoute avec le statut « En attente d'analyse ».

Le scénario n'exigera ni scan téléphonique, ni tunnel public, ni accès au réseau local.

## 5. Données de démonstration

### 5.1 Principes

Le dépôt ne contiendra pas les 15 308 annotations complètes. Il contiendra un petit ensemble de démonstration, synthétique ou anonymisé, construit selon la structure du corpus validé.

Chaque exemple exposera au minimum :

```text
text
sentiment_label
channel
aspect
source_url
timestamp
confidence
language
evidence
intent
alert
```

Les canaux seront limités à `facebook`, `google_maps`, `audio` et `youtube`. Les exemples couvriront le français, le script arabe, la darija, l'arabizi et les formulations mixtes. Les aspects métier visibles seront notamment le goût, l'emballage, le prix, la disponibilité et la fraîcheur.

Les URL utiliseront un domaine non réel de démonstration. Aucun nom, compte, numéro de téléphone ou emplacement personnel ne sera conservé.

### 5.2 Justification auditable

L'interface montrera une **trace de justification supervisée**, pas une chaîne de pensée cachée :

1. commentaire original ;
2. extrait exact servant de preuve ;
3. interprétation courte ;
4. sortie structurée ;
5. confiance et validation humaine éventuelle.

Le libellé « Analyse du SLM — exemple de démonstration » empêchera de laisser croire que le modèle en cours d'entraînement a produit en direct les résultats affichés.

### 5.3 Scénario métier cohérent

Le scénario central sera unique :

```text
hausse des avis sur l'indisponibilité à Oran
→ commentaires sources multilingues
→ aspect disponibilité détecté
→ alerte localisée
→ recommandation de vérification et de réapprovisionnement ciblé
```

Les autres exemples serviront uniquement à montrer la diversité linguistique et les sorties structurées. Aucun écran ne mélangera un problème de goût avec une action de distribution sans preuve correspondante.

## 6. Préparation Windows

Trois scripts seront fournis dans un dossier dédié :

- `INSTALLER_DEMO_LETICIA.ps1` : vérifie Node.js, installe les dépendances avec `npm ci` et prépare la configuration locale ;
- `LANCER_DEMO_LETICIA.ps1` : démarre le frontend, attend sa disponibilité et ouvre le parcours initial ;
- `REINITIALISER_DEMO.ps1` : ouvre la route de réinitialisation ou efface uniquement les clés locales de la démonstration.

Les scripts devront :

- résoudre leurs chemins depuis leur propre emplacement ;
- ne jamais écrire de clé privée ;
- produire des erreurs en français avec une action corrective ;
- détecter un port 5173 déjà occupé ;
- ne pas fermer un processus qu'ils n'ont pas créé ;
- arrêter proprement le serveur lancé par le script.

## 7. Documents remis à Leticia

Le dépôt contiendra un dossier `docs/protomarket_ii_2026/demo_leticia/` avec :

- `00_LIRE_EN_PREMIER.md` ;
- `01_INSTALLATION_WINDOWS.md` ;
- `02_SCRIPT_VIDEO_PROTOTYPE.md` ;
- `03_SCRIPT_PITCH_3_MINUTES.md` ;
- `04_CHECKLIST_AVANT_TOURNAGE.md` ;
- `05_DEPANNAGE_RAPIDE.md` ;
- `06_MESSAGE_A_ENVOYER_A_LETICIA.md`.

Le script de la vidéo du prototype indiquera, pour chaque séquence : durée, page, clic exact, texte à prononcer et élément à ne pas montrer. Le pitch de trois minutes restera distinct de la démonstration technique.

## 8. Storyboard de la vidéo prototype

Durée cible : 1 min 45 à 2 min.

1. **0:00–0:12 — Situation** : avis dispersés et multilingues.
2. **0:12–0:28 — Origine des signaux** : Facebook, Google Maps, YouTube, audio autorisé et QR.
3. **0:28–0:43 — Surveillance** : disponibilité d'un produit à Oran.
4. **0:43–1:03 — Compréhension SLM** : commentaire, preuve exacte et sortie structurée.
5. **1:03–1:23 — QR** : point d'écoute, QR, formulaire dans un second onglet et envoi.
6. **1:23–1:42 — Signal** : alerte disponibilité et commentaires sources.
7. **1:42–1:55 — Action** : vérification puis réapprovisionnement ciblé, avec décision humaine.
8. **1:55–2:00 — Conclusion** : prototype actuel et prochaine étape d'industrialisation.

## 9. Storyboard du pitch de trois minutes

Le pitch couvrira :

- LIDAL et l'équipe ;
- le problème des avis algériens multilingues ;
- la méthode métier → données spécialisées → SLM → produit ;
- LIDAL AI comme moteur en cours de validation ;
- LIDAL Pulse comme premier produit ;
- RamyPulse et Alerte IA comme expériences fondatrices, sans les présenter comme clients de LIDAL ;
- le marché, le modèle économique et le financement ProtoMarket ;
- l'objectif de pilote et d'industrialisation.

## 10. Identité visuelle

Les logos officiels transmis par Leticia seront copiés dans `frontend/client/public/brand/` avec des noms stables et sans espaces. L'application utilisera la variante adaptée au fond sombre. Les documents de tournage indiqueront quelle variante employer pour la miniature et les écrans de conclusion.

Aucun autre changement de design général ne sera introduit dans cette livraison.

## 11. Gestion des erreurs et sécurité

- Le mode démonstration sera explicitement signalé dans l'interface.
- Les mutations resteront locales et réversibles.
- Les retours audio ne seront pas téléversés ; seule une représentation locale de démonstration sera conservée.
- Aucune clé `.env`, donnée brute d'entraînement ou base SQLite locale ne sera commitée.
- Le formulaire public ne sera pas présenté comme publiquement déployé.
- L'interface ne prétendra pas collecter tous les réseaux sociaux en temps réel.
- Le SLM en entraînement ne sera pas présenté comme déjà intégré en production.

## 12. Vérification

Avant publication de la branche :

```powershell
cd frontend
npm ci
npm run check
npm run build
npm run test:quality
```

Des tests Playwright couvriront au minimum :

- chargement du parcours déterministe ;
- présence des quatre canaux autorisés ;
- affichage d'un exemple multilingue avec preuve exacte ;
- ouverture du point d'écoute et présence du QR ;
- ouverture du formulaire public dans un second onglet ;
- soumission d'un retour avec consentement ;
- retour visible avec statut en attente ;
- réinitialisation de la démonstration ;
- absence de requête externe pendant le parcours filmé.

Une validation manuelle finale sera réalisée en 1920 × 1080, zoom 100 %, avec le script de Leticia suivi de bout en bout.

## 13. Stratégie Git et livraison

Les changements seront limités à la branche `codex/lidal-pulse-leticia-demo`. Les modifications existantes appartenant à d'autres worktrees ne seront ni écrasées ni incluses par accident.

Les commits seront séparés par responsabilité :

1. parcours QR et données de démonstration ;
2. scripts Windows ;
3. tests ;
4. guides et scripts vidéo ;
5. identité visuelle, si elle n'est pas déjà intégrée.

La branche sera poussée sur `origin` uniquement après réussite des vérifications. Le message final destiné à Leticia donnera la commande de clonage, la branche, la commande d'installation, la commande de lancement et le numéro du commit validé.

## 14. Hors périmètre

- déploiement public du formulaire QR ;
- utilisation du téléphone pour scanner le QR pendant le tournage ;
- intégration du checkpoint encore en entraînement ;
- collecte réelle de réseaux sociaux pendant la vidéo ;
- publication du corpus complet d'entraînement ;
- modification du backend historique ou du schéma partagé ;
- refonte générale du design de LIDAL Pulse.
