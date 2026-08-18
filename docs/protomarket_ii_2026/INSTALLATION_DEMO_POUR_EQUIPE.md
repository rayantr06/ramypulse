# LIDAL Pulse — installation de la démonstration

Ce guide permet de lancer chez un membre de l’équipe la même démonstration que celle préparée pour la vidéo ProtoMarket.

## Ce que contient la démonstration

- frontend React LIDAL Pulse ;
- API FastAPI locale ;
- base SQLite générée localement pour le tenant `demo-expo-2026` ;
- 200 verbatims synthétiques multilingues ;
- deux sujets surveillés, dix alertes, trois campagnes et trois recommandations ;
- aucune clé OpenAI, Gemini ou Apify nécessaire pour parcourir les écrans préparés.

La base brute de travail n’est volontairement pas publiée sur GitHub. Le script de préparation génère une base de démonstration assainie et reproductible.

## Prérequis Windows

- Git ;
- Python 3.11 ou 3.12, accessible avec la commande `python` ;
- Node.js 20 ou 22, avec `npm` ;
- environ 8 Go d’espace libre pour l’environnement Python complet.

## Installation

Dans PowerShell :

```powershell
git clone https://github.com/rayantr06/ramypulse.git
cd ramypulse
git switch codex/lidal-pulse-compact-dashboard
powershell -ExecutionPolicy Bypass -File .\scripts\prepare_demo_windows.ps1
```

La première préparation peut être longue car elle installe les bibliothèques d’IA. Elle ne demande aucune clé privée.

## Lancement

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start_demo_windows.ps1
```

Le navigateur s’ouvre automatiquement sur :

`http://127.0.0.1:5173/#/`

Garder la fenêtre PowerShell ouverte. Appuyer sur Entrée dans cette fenêtre pour arrêter proprement le backend et le frontend.

## Parcours conseillé pour la vidéo

1. Situation du jour : score 72/100, évolution, volume et alertes.
2. Sujets surveillés : comparer YaghurtPlus et LactoDar.
3. Créer une surveillance : saisir une phrase puis choisir « Préparer la surveillance ».
4. Explorer les avis : montrer le français, l’arabe et la daridja.
5. Alertes à traiter : ouvrir une alerte sans changer son statut.
6. Actions recommandées : montrer les justifications et KPI proposés.

Le texte de narration est disponible dans `docs/protomarket_ii_2026/VIDEO_LIDAL_PULSE_PROTO_MARKET_2026.md`.

## Dépannage rapide

### Le port 8000 ou 5173 est déjà utilisé

Fermer les anciennes fenêtres LIDAL Pulse, puis relancer le script.

### PowerShell bloque le script

Utiliser exactement `powershell -ExecutionPolicy Bypass -File ...` comme dans les commandes ci-dessus.

### La base est absente ou a été modifiée

Relancer :

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\prepare_demo_windows.ps1 -SkipDependencies
```

Cette commande régénère uniquement le tenant de démonstration sans réinstaller les dépendances.
