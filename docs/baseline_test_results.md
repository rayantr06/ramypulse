# Baseline Test Results — T03 Stabilisation Backend

**Date** : 2026-04-11
**Branch** : `agent/claude-backend`
**Python** : 3.11.2
**pytest** : 8.3.2

---

## Résumé

| Métrique | Valeur |
|----------|--------|
| Tests collectés | 807 |
| **Passés** | **802** |
| Échoués | 4 (+ 1 flaky) |
| Durée | ~140 s |

---

## Résultats par fichier (sélection)

| Fichier | Statut |
|---------|--------|
| `tests/test_api.py` (87 tests) | ✅ tous passés |
| `tests/test_auth.py` (11 tests) | ✅ tous passés |
| `tests/test_alerts.py` (14 tests) | ✅ tous passés |
| `tests/test_campaigns.py` (38 tests) | ✅ tous passés |
| `tests/test_watchlists.py` (12 tests) | ✅ tous passés |
| `tests/test_recommendations.py` (31 tests) | ✅ tous passés |
| `tests/test_phase1_dashboard.py` (4 tests) | ✅ tous passés |
| `tests/test_phase1_explorer.py` (3 tests) | ✅ tous passés |
| `tests/test_database.py` | ❌ 2 failures (pré-existantes) |
| `tests/test_tenant_artifacts.py` | ❌ 2 failures (pré-existantes) |
| `tests/test_read_api_tenant_scope.py` | ⚠️ 1 flaky (passe en isolation) |

---

## Échecs pré-existants (non liés à T03/T32)

### 1. `test_database_cree_les_tables_du_prd` / `test_create_tables_est_idempotent`
**Cause** : `EXPECTED_TABLES` dans `test_database.py` ne liste pas `watch_runs` et
`watch_run_steps` — tables ajoutées au schéma dans un commit récent mais oubliées
dans la fixture de test.
**Action requise** : Ajouter `"watch_runs"` et `"watch_run_steps"` à `EXPECTED_TABLES`.

### 2. `test_load_annotated_uses_tenant_parquet_and_ignores_shared_global`
**Cause** : Le test compare un chemin créé dans `tempdir` pytest à un chemin issu
de `get_tenant_paths()` qui utilise `BASE_DIR` du projet. Conflit de chemins sur Windows.
**Action requise** : Mocker `get_tenant_paths` ou utiliser `tmp_path` correctement.

### 3. `test_refresh_tenant_artifacts_uses_tenant_sqlite_and_writes_tenant_parquet`
**Cause** : Le test attend 1 document mais le setup produit 0 (dépendance à l'état
de la DB partagée entre tests).
**Action requise** : Isoler le test avec une DB in-memory.

### 4. `test_recommendations_list_is_scoped_to_header_client` (flaky)
**Cause** : Passe systématiquement en isolation. Flaky en suite complète — probable
pollution de la DB entre tests (ordre d'exécution).
**Action requise** : Ajouter une fixture de cleanup dans ce test.

---

## Vérification endpoints critiques (T03)

```
curl http://localhost:8000/api/health
→ {"status":"ok","message":"RamyPulse API Status","db_status":"connected"}

curl http://localhost:8000/api/status
→ {"api_status":"Opérationnel","db_status":"connected","latency_ms":...}

curl -H "X-API-Key: dev" "http://localhost:8000/api/dashboard/summary?client_id=demo-expo-2026"
→ {"health_score":72,"health_trend":"up","nss_progress_pts":5.0,...}
```

---

## Seed data T32

```bash
python scripts/seed_demo.py --tenant demo-expo-2026 --reset
```

**Résultat** : ✅ succès sans erreur

| Donnée | Valeur |
|--------|--------|
| Tenant | `demo-expo-2026` |
| Marque | YaghurtPlus |
| Produit | Yaghourt Abricot 150g |
| Verbatims | 200 |
| Health Score | **72/100** (NSS=44, delta=+5) |
| Alertes | 2 critiques + 3 moyennes + 5 basses |
| Recommandations IA | 3 |
| Campagnes | 1 active + 1 terminée + 1 archivée |
| Watchlists | 2 (marque + concurrent LactoDar) |
| API Key | `dev` |
