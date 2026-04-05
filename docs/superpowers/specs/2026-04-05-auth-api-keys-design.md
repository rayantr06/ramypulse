# Auth API Keys — Design Spec

**Date:** 2026-04-05
**Branche:** `feat/auth-access-control`
**Scope:** Lot A du plan multi-agents (MULTI_AGENT_EXECUTION_GAPS.md)

---

## 1. Probleme

L'API FastAPI RamyPulse est entierement ouverte. Aucun header, aucun token, aucun controle d'acces. Quiconque connait l'URL peut lire et ecrire toutes les donnees de tous les clients. Le PRD v2.0 (section 14.1) exige un middleware qui injecte le `client_id` depuis le contexte d'authentification.

## 2. Solution retenue

**API Key + table `api_keys` en base.**

Chaque requete protegee doit envoyer un header `X-API-Key`. Le backend hash la cle, la cherche en base, et en deduit le `client_id`. Pas de JWT, pas de login form, pas de session.

### Pourquoi ce choix

- **API Key statique (rejetee)** : une seule cle en env, pas de rotation, pas de multi-client.
- **JWT login (rejetee)** : necessite une table users, un formulaire de login, du refresh token. Overkill pour un PoC mono-client sans UI de login.
- **API Key en base (retenue)** : protection reelle, multi-client, rotation, desactivation. Simple a implementer (une table, un middleware, un `Depends`).

## 3. Data model

### Table `api_keys`

```sql
CREATE TABLE IF NOT EXISTS api_keys (
    key_id      TEXT PRIMARY KEY,
    client_id   TEXT NOT NULL,
    key_hash    TEXT NOT NULL,
    key_prefix  TEXT NOT NULL,
    label       TEXT,
    scopes      TEXT DEFAULT '["*"]',
    is_active   INTEGER DEFAULT 1,
    created_at  TEXT NOT NULL,
    last_used_at TEXT
)
```

| Colonne | Role |
|---|---|
| `key_id` | UUID, identifiant interne |
| `client_id` | Le client associe a cette cle |
| `key_hash` | SHA-256 de la cle brute. La cle brute n'est JAMAIS stockee. |
| `key_prefix` | 8 premiers caracteres de la cle. Pour les logs et l'UI admin. |
| `label` | Nom lisible ("Frontend dev", "CI pipeline") |
| `scopes` | JSON array de permissions. `["*"]` = acces complet. Extensible plus tard. |
| `is_active` | 0 = cle desactivee, toute requete avec cette cle sera refusee |
| `created_at` | Timestamp ISO de creation |
| `last_used_at` | Timestamp ISO de derniere utilisation. Mis a jour a chaque requete. |

### Format de la cle brute

`rpk_{32 hex chars}` — exemple : `rpk_a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6`

Le prefixe `rpk_` (RamyPulse Key) rend les cles identifiables dans les logs et les outils de detection de secrets.

## 4. Auth dependency

### Nouveau fichier : `core/security/auth.py`

```python
AuthContext = namedtuple("AuthContext", ["client_id", "key_id", "scopes"])

def get_current_client(x_api_key: str = Header(...)) -> AuthContext:
    """FastAPI dependency. Hash la cle, lookup en base, retourne le contexte."""
```

Comportement :
- Header `X-API-Key` absent → `401 Unauthorized`
- Cle inconnue ou inactive → `401 Unauthorized`
- Cle valide → retourne `AuthContext(client_id, key_id, scopes)`, update `last_used_at`

Le body de la 401 sera : `{"detail": "Invalid or missing API key"}`
Pas de distinction entre "absent" et "invalide" pour eviter le timing oracle.

## 5. Protection des endpoints

### Public (pas d'auth)

- `GET /` (redirect vers /docs)
- `GET /api/health`
- `/docs`, `/openapi.json`, `/redoc`

### Protege (auth requise)

Tous les routers metier :
- `dashboard.router`
- `alerts.router`
- `watchlists.router`
- `campaigns.router`
- `recommendations.router`
- `explorer.router`
- `social_metrics.router`

L'injection se fait dans `api/main.py` via le parametre `dependencies=[Depends(get_current_client)]` sur chaque `include_router` protege.

### Hors scope (Lot B)

- `admin.router` — pas touche dans ce lot. L'auth sera branchee a l'integration.

## 6. Key management endpoints

### Nouveau router : `api/routers/auth.py`

| Methode | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/auth/keys` | Oui | Cree une cle. Retourne la cle brute UNE SEULE FOIS. |
| `GET` | `/api/auth/keys` | Oui | Liste les cles (prefix + label + active + dates). Jamais le hash. |
| `DELETE` | `/api/auth/keys/{key_id}` | Oui | Desactive une cle (soft delete : `is_active = 0`). |

#### POST /api/auth/keys

Request body :
```json
{
  "client_id": "ramy_client_001",
  "label": "Frontend dev"
}
```

Response (201) :
```json
{
  "key_id": "key-abc123",
  "client_id": "ramy_client_001",
  "key_prefix": "rpk_a1b2",
  "label": "Frontend dev",
  "api_key": "rpk_a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6",
  "warning": "Store this key securely. It will not be shown again."
}
```

Le champ `api_key` n'apparait que dans cette reponse. Jamais dans GET, jamais en base.

#### GET /api/auth/keys

Response (200) :
```json
[
  {
    "key_id": "key-abc123",
    "client_id": "ramy_client_001",
    "key_prefix": "rpk_a1b2",
    "label": "Frontend dev",
    "is_active": true,
    "created_at": "2026-04-05T10:00:00",
    "last_used_at": "2026-04-05T12:30:00"
  }
]
```

## 7. Seed key au premier demarrage

Dans `create_tables()` de `core/database.py` :
- Si la table `api_keys` existe et est vide → generer une cle pour `ramy_client_001`
- Logger la cle en `WARNING` : `"Initial API key generated for ramy_client_001: rpk_xxxx... Store it securely."`
- Ceci ne se produit qu'une seule fois (si la table est vide).

## 8. Fichiers modifies

| Fichier | Action |
|---|---|
| `core/database.py` | Ajouter table `api_keys` dans `_SCHEMA_STATEMENTS` + seed key dans `create_tables()` |
| `core/security/auth.py` | NOUVEAU — dependency `get_current_client` |
| `api/routers/auth.py` | NOUVEAU — CRUD cles |
| `api/schemas.py` | Ajouter `ApiKeyCreate`, `ApiKeyResponse`, `ApiKeyCreatedResponse` |
| `api/main.py` | Ajouter `dependencies=[Depends(get_current_client)]` sur les routers proteges, inclure `auth.router` |
| `tests/test_auth.py` | NOUVEAU — tests unitaires auth |

### Fichiers NON touches

- `api/routers/admin.py` — scope Lot B
- `frontend/` — scope interdit
- `core/alerts/`, `core/ingestion/`, `core/social_metrics/` — scope interdit

## 9. Tests

| Test | Verifie |
|---|---|
| `test_health_no_auth` | GET /api/health repond 200 sans header |
| `test_protected_no_key` | GET /api/dashboard/summary repond 401 sans header |
| `test_protected_bad_key` | GET /api/dashboard/summary avec cle invalide repond 401 |
| `test_protected_valid_key` | GET /api/dashboard/summary avec cle valide repond 200 |
| `test_deactivated_key` | Cle desactivee repond 401 |
| `test_create_key` | POST /api/auth/keys retourne la cle brute + key_id |
| `test_list_keys` | GET /api/auth/keys retourne prefix, pas de hash |
| `test_delete_key` | DELETE /api/auth/keys/{id} desactive la cle |
| `test_client_id_injected` | Le contexte auth porte le bon client_id |

## 10. Limites connues

- Pas de rate limiting (a ajouter plus tard)
- Pas de scopes granulaires (tout est `["*"]` pour l'instant)
- Pas de refresh/rotation automatique
- Les routes admin restent ouvertes (Lot B)
- Le frontend devra envoyer `X-API-Key` — documentation dans le resume de merge
