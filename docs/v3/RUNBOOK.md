# LIDAL Pulse V3 — guide d’exécution et de déploiement

## Démonstration locale

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Ouvrir `http://127.0.0.1:5173/#/`. La V3 utilise ses données de démonstration
tant que `VITE_LIDAL_V3_API_ENABLED` n’est pas égal à `true`.

### Service V3 local

```powershell
python -m pip install -r services/v3_api/requirements.txt
./scripts/run_lidal_v3.ps1 -DemoAuth
```

Le service écoute sur `http://127.0.0.1:8001`. Le proxy Vite envoie `/api/v3`
vers ce port et conserve `/api` vers le backend historique sur le port 8000.

Le mode `-DemoAuth` est strictement local. Il ne doit jamais être activé sur un
environnement accessible publiquement.

## Variables serveur

```text
SUPABASE_URL=
SUPABASE_JWT_AUDIENCE=authenticated
LIDAL_V3_DB_PATH=data/lidal_v3.sqlite3
YOUTUBE_API_KEY=
APIFY_API_KEY=
APIFY_FACEBOOK_ACTOR_ID=
APIFY_TIKTOK_ACTOR_ID=
APIFY_GOOGLE_MAPS_ACTOR_ID=
```

Les jetons fournisseurs, la clé YouTube et toute clé Supabase `service_role`
restent exclusivement côté serveur.

## Variables frontend

```text
VITE_LIDAL_V3_API_ENABLED=true
VITE_LIDAL_V3_API_BASE_URL=https://api.example.dz
VITE_SUPABASE_URL=https://project.supabase.co
VITE_SUPABASE_ANON_KEY=
```

Le navigateur envoie un JWT utilisateur dans `Authorization` et
`X-Organization-Id`. Le backend revalide les deux avant chaque transaction.

## Vérification avant déploiement

```powershell
python -m pytest tests/test_v3_product_foundation.py
python -m py_compile services/v3_api/*.py

cd frontend
npm run check
npm run build
npm run test:quality
```

## Ordre de déploiement pilote

1. Créer le projet Supabase pilote et appliquer la migration versionnée.
2. Créer deux organisations de test et vérifier les tests IDOR/BOLA dans les
   deux sens.
3. Déployer FastAPI sur VPS avec HTTPS, variables serveur et `dev auth` absent.
4. Configurer `VITE_LIDAL_V3_API_BASE_URL` sur Vercel puis redéployer le
   frontend.
5. Vérifier `Aujourd’hui → signal → preuve → dossier → action` avec un JWT réel.
6. Brancher un seul connecteur à la fois, avec quota faible et arrêt budgétaire.
7. N’activer des données identifiantes qu’après la revue juridique et ANPDP.

## Règles d’exploitation

- Une annotation `pending` ou `failed` est exclue des KPI mais le document brut
  reste traçable.
- Un signal ne peut exister sans preuve reliée.
- Toute mutation requiert une clé d’idempotence et produit un événement.
- Aucun brouillon de l’agent n’assigne, n’envoie, ne publie ou ne clôture.
- La fraîcheur, la couverture partielle, le coût et les erreurs restent visibles.
