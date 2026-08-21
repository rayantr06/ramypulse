# Dépannage rapide

## Le script refuse Node.js

La démo accepte Node.js 20 ou 22. Vérifiez :

```powershell
node --version
npm --version
```

Installez une version LTS compatible, fermez PowerShell, rouvrez-le, puis relancez l’installateur.

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

Relancez ensuite l’installateur puis le lanceur. N’utilisez pas une image depuis Google Drive ou un CDN pendant le tournage.

## L’affichage est coupé

Réglez Windows et le logiciel de capture sur 1920 × 1080, puis le zoom du navigateur à 100 %. Masquez la barre des favoris si elle réduit la hauteur utile. Ne réduisez pas le zoom pour faire entrer davantage d’éléments.

## Une prise a modifié l’état

Fermez le second onglet, exécutez `REINITIALISER_DEMO.ps1` et recommencez la vidéo depuis la scène 1. N’essayez pas de reconstituer manuellement l’état intermédiaire.
