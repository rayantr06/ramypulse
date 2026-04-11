# PROMPT P0-01 — Claude Code : Stabiliser le backend + Seed data
**Phase** : 0 — Stabilisation (Jour 1)
**Agent** : Claude Code (worktree backend)
**Tâches** : T03, T32

---

```
CONTEXTE :
Tu travailles sur RamyPulse, une application de veille marketing algérienne.
Backend FastAPI + SQLite, 51 endpoints, 33 tables.
Worktree : agent/claude-backend
Ton fichier de config : CLAUDE.md (lis-le en premier)

IMPORTANT : Tu es peut-être sur Windows (PowerShell) ou Linux/macOS.
Détecte ton environnement avant d'exécuter des commandes shell.

FICHIERS À LIRE EN PRIORITÉ :
1. CLAUDE.md
2. api/main.py
3. requirements.txt
4. tests/ (lister les fichiers)

═══ TÂCHE T03 — Vérification et stabilisation backend ═══

1. Préparer l'environnement Python :
   # Si .venv existe déjà :
   #   Linux/macOS/Git Bash : source .venv/bin/activate
   #   PowerShell Windows   : .\.venv\Scripts\Activate.ps1
   # Sinon :
   python -m venv .venv
   pip install -r requirements.txt

2. Lancer le backend :
   uvicorn api.main:app --reload --port 8000
   # Note : pas de & en fin de commande sur PowerShell

3. Vérifier les endpoints critiques (dans un autre terminal) :
   curl http://localhost:8000/api/health
   curl http://localhost:8000/api/status
   curl -H "X-API-Key: dev" http://localhost:8000/api/dashboard/summary
   # PowerShell natif (si curl n'est pas disponible) :
   # Invoke-RestMethod http://localhost:8000/api/health

4. Si des erreurs d'import → corriger UNIQUEMENT les imports manquants

5. Lancer les tests et sauvegarder le résultat :
   pytest tests/ -v --tb=short
   # Sauvegarder la sortie dans docs/baseline_test_results.md

6. Créer docs/baseline_test_results.md avec le résultat des tests
   (copier la sortie de pytest, noter les tests qui passent et échouent)

═══ TÂCHE T32 — Seed data démo (APRÈS que backend démarre) ═══

Créer scripts/seed_demo.py qui peuple la DB pour la démo expo :

- Tenant : client_id="demo-expo-2026", brand="YaghurtPlus", product="Yaghourt Abricot 150g"
- 200 verbatims réalistes en darija/français :
  • Facebook 40%, Google Maps 35%, YouTube 25%
  • Sentiments : 40% positif, 30% neutre, 20% negatif, 10% tres_negatif
  • Wilayas : Alger, Oran, Constantine, Annaba, Tlemcen
  • Aspects : goût, texture, prix, disponibilité, packaging
- Score santé dashboard : 72/100, tendance +5
- 2 alertes critiques, 3 moyennes, 5 basses
- 3 recommandations IA pré-générées avec priorité/rationale/KPI
- 3 campagnes (1 active, 1 archivée, 1 terminée)
- 2 watchlists actives (marque + concurrent "LactoDar")

Options du script : --reset pour effacer et recréer
Commande finale : python scripts/seed_demo.py --tenant demo-expo-2026 --reset

CONTRAINTES :
- Ne pas toucher aux fichiers frontend/client/src/
- Ne pas modifier frontend/shared/schema.ts
- Committer sur la branche agent/claude-backend uniquement
- Messages de commit : "feat(seed): add demo data seed script for expo"

CRITÈRES DE SUCCÈS :
✅ curl http://localhost:8000/api/health → {"status": "ok"}
✅ python scripts/seed_demo.py --tenant demo-expo-2026 --reset → sans erreur
✅ curl -H "X-API-Key: dev" http://localhost:8000/api/dashboard/summary?client_id=demo-expo-2026 → healthScore: 72
✅ pytest tests/ -v → baseline documenté dans docs/baseline_test_results.md
```
