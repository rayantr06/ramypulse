# Dépannage rapide

## Le script refuse Node.js

La démo accepte Node.js 20 à partir de **20.19.0**, ou Node.js 22 à partir de **22.12.0**. Les versions 20.18.x, 22.11.x et les autres versions majeures sont refusées. Vérifiez :

```powershell
node --version
npm --version
```

Installez une version compatible dans l’une de ces deux lignes majeures, fermez PowerShell, rouvrez-le, puis relancez l’installateur.

## `npm ci` échoue

Vérifiez la connexion internet et que vous êtes sur la bonne branche :

```powershell
git status --short --branch
git switch codex/lidal-pulse-leticia-demo
powershell -ExecutionPolicy Bypass -File .\scripts\leticia\INSTALLER_DEMO_LETICIA.ps1
```

Ne modifiez pas `package-lock.json` pour contourner l’erreur.

## Le port 5173 est déjà utilisé

Fermez l’ancienne fenêtre de lancement LIDAL Pulse en appuyant sur Entrée. Si une autre application utilise le port, arrêtez cette application vous-même, puis relancez `LANCER_DEMO_LETICIA.ps1`. Le script ne tue jamais un processus inconnu.

## Le navigateur ne s’ouvre pas

Laissez le lanceur ouvert, puis saisissez manuellement :

`http://127.0.0.1:5173/#/`

Si la page ne répond pas après 30 secondes, lisez le message français du lanceur, corrigez le prérequis indiqué et relancez-le.

## Le mauvais espace ou un état ancien apparaît

Pendant que la démo tourne :

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\leticia\REINITIALISER_DEMO.ps1
```

Attendez le retour à l’accueil. L’espace attendu est `LIDAL · Démo métier`.

## **Tester le formulaire** n’ouvre pas le second onglet

Autorisez les nouveaux onglets pour `127.0.0.1`, puis cliquez directement une seule fois sur le lien. N’utilisez pas de téléphone, QR scanner, tunnel ou URL publique. Si un onglet existe déjà, fermez-le et recommencez après réinitialisation.

## Le retour QR n’apparaît pas dans le premier onglet

Dans le second onglet, vérifiez les trois entrées obligatoires : une note, un message et le consentement. Après **En attente d’analyse**, revenez au premier onglet **Points d’écoute** et actualisez la page.

## Le logo ou le favicon manque

Vérifiez que ces deux fichiers existent dans le clone :

- `frontend/client/public/brand/lidal-mark-dark.png` ;
- `frontend/client/public/brand/lidal-mark-transparent.png`.

L’installateur ne restaure pas les fichiers suivis par Git. Si vous êtes dans un checkout Git valide et que vous voulez récupérer exactement les deux copies de la branche, vérifiez d’abord l’état ciblé :

```powershell
git rev-parse --is-inside-work-tree
git branch --show-current
git status --short -- frontend/client/public/brand/lidal-mark-dark.png frontend/client/public/brand/lidal-mark-transparent.png
git restore --source=HEAD -- frontend/client/public/brand/lidal-mark-dark.png frontend/client/public/brand/lidal-mark-transparent.png
```

Les deux premières commandes doivent afficher `true`, puis `codex/lidal-pulse-leticia-demo`. La dernière commande remplace uniquement les modifications locales de ces deux assets. Si le dossier n’est pas un checkout Git valide, n’est pas sur cette branche, ou si cette récupération ciblée échoue, conservez le dossier actuel et créez un clone propre à côté :

```powershell
cd ..
git clone https://github.com/rayantr06/ramypulse.git ramypulse-leticia-propre
cd ramypulse-leticia-propre
git switch codex/lidal-pulse-leticia-demo
```

Exécutez ensuite l’installateur puis le lanceur depuis le checkout récupéré ou le clone propre. N’utilisez pas une image depuis Google Drive ou un CDN pendant le tournage.

## L’affichage est coupé

Réglez Windows et le logiciel de capture sur 1920 × 1080, puis le zoom du navigateur à 100 %. Masquez la barre des favoris si elle réduit la hauteur utile. Ne réduisez pas le zoom pour faire entrer davantage d’éléments.

## Une prise a modifié l’état

Fermez le second onglet, exécutez `REINITIALISER_DEMO.ps1` et recommencez la vidéo depuis la scène 1. N’essayez pas de reconstituer manuellement l’état intermédiaire.
