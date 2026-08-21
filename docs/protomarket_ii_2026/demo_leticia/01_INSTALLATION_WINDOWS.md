# Installation Windows — démonstration Leticia

## Prérequis

- Windows 10 ou 11 ;
- Git ;
- Node.js 20 à partir de **20.19.0**, ou Node.js 22 à partir de **22.12.0**, avec `npm` ;
- une connexion internet pour le clonage et `npm ci` uniquement.

Le parcours enregistré est ensuite frontend-only : aucun Python, backend, compte fournisseur ou clé API n’est requis.

## Première installation

Ouvrez PowerShell dans le dossier où vous voulez installer la démo, puis exécutez exactement :

```powershell
git clone https://github.com/rayantr06/ramypulse.git
cd ramypulse
git switch codex/lidal-pulse-leticia-demo
powershell -ExecutionPolicy Bypass -File .\scripts\leticia\INSTALLER_DEMO_LETICIA.ps1
```

Le script vérifie la version complète de Node.js, installe les dépendances du frontend avec `npm ci` et prépare `.env.local` seulement s’il n’existe pas déjà. Les autres versions majeures ne sont pas acceptées pour ce paquet de démonstration.

## Lancer la démo

Depuis la racine `ramypulse` :

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\leticia\LANCER_DEMO_LETICIA.ps1
```

Le navigateur doit ouvrir `http://127.0.0.1:5173/#/`. Gardez PowerShell ouvert pendant la répétition. À la fin, revenez dans cette fenêtre et appuyez sur Entrée : le script arrête uniquement le processus Vite qu’il a lancé.

## Réinitialiser avant chaque prise

Pendant que la démo tourne, ouvrez un second PowerShell à la racine du dépôt :

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\leticia\REINITIALISER_DEMO.ps1
```

La page locale de réinitialisation efface uniquement l’état de la démonstration Leticia, puis revient à l’accueil. Elle ne supprime aucun fichier et ne touche pas aux autres données du navigateur.

## Contrôle rapide

Vérifiez avant de répéter :

- le logo LIDAL officiel apparaît en haut de l’application ;
- l’espace affiché est `LIDAL · Démo métier` ;
- l’accueil montre le flux Facebook, Google Maps, YouTube, Audio autorisé et QR ;
- le lien **Tester le formulaire** de la page **Points d’écoute** ouvre un second onglet.

En cas d’échec, utilisez [05_DEPANNAGE_RAPIDE.md](05_DEPANNAGE_RAPIDE.md).
