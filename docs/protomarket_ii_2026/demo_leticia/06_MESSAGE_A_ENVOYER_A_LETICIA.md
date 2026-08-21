# Message à envoyer à Leticia

Bonjour Leticia,

La démonstration LIDAL Pulse pour ProtoMarket est préparée sur une branche dédiée. Sur un PC Windows avec Git et Node.js 20 ou 22, ouvre PowerShell et exécute exactement :

```powershell
git clone https://github.com/rayantr06/ramypulse.git
cd ramypulse
git switch codex/lidal-pulse-leticia-demo
powershell -ExecutionPolicy Bypass -File .\scripts\leticia\INSTALLER_DEMO_LETICIA.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\leticia\LANCER_DEMO_LETICIA.ps1
```

Le navigateur s’ouvrira sur `http://127.0.0.1:5173/#/`. Garde la fenêtre PowerShell ouverte. Pour arrêter proprement la démo, reviens dans cette fenêtre et appuie sur Entrée.

Avant chaque prise, pendant que la démo tourne, réinitialise le parcours avec :

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\leticia\REINITIALISER_DEMO.ps1
```

Les guides sont dans `docs/protomarket_ii_2026/demo_leticia/`. Commence par `00_LIRE_EN_PREMIER.md`, puis suis `02_SCRIPT_VIDEO_PROTOTYPE.md` scène par scène. Le pitch de trois minutes est séparé dans `03_SCRIPT_PITCH_3_MINUTES.md`.

Pour l’enregistrement :

- filme en **1920 × 1080**, zoom navigateur **100 %** ;
- masque les notifications, terminaux, secrets, favoris sensibles et onglets personnels ;
- pour le QR, utilise uniquement **Tester le formulaire** : le flux préparé s’ouvre dans un second onglet du même ordinateur ;
- ne montre jamais de terminal, clé, mot de passe, chemin personnel ou fichier privé dans la vidéo ;
- dis clairement que le SLM est en validation et que les sorties sont préparées ;
- ne prétends pas que les canaux sont collectés en direct ;
- présente RamyPulse et Alerte IA comme expériences fondatrices, et Ramy uniquement comme client potentiel pour une expérimentation ;
- rappelle que la vérification du stock et la décision de réassort restent humaines.

Si quelque chose bloque, consulte `05_DEPANNAGE_RAPIDE.md` avant de modifier la démo.
