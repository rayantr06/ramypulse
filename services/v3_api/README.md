# Service LIDAL Pulse V3

Service FastAPI additif. Il reste hors de `api/` afin de ne pas modifier la zone
de compatibilite historique.

```powershell
$env:LIDAL_V3_ALLOW_DEV_AUTH="true"
$env:LIDAL_V3_DB_PATH="data/lidal_v3.sqlite3"
python -m uvicorn services.v3_api.main:app --port 8001 --reload
```

En production, ne pas activer `LIDAL_V3_ALLOW_DEV_AUTH`. Configurer
`SUPABASE_URL`, envoyer `Authorization: Bearer <JWT>` et selectionner
l'organisation avec `X-Organization-Id`. Le service verifie la signature via le
JWKS Supabase et ne lit jamais les roles depuis `user_metadata`.
