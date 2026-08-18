# Déploiement pilote V3 — LIDAL SLM V0.4 et Apify

**Branche :** `codex/lidal-pulse-v3`

**Principe :** la version de démonstration reste intacte ; cette procédure concerne
uniquement le pilote V3.

## 1. Architecture réellement branchée

```text
Surveillance LIDAL Pulse
  ├─ Facebook / Instagram / Google Maps → Apify
  ├─ Google Maps en repli → Places API officielle
  └─ autres sources → collecteurs existants
             ↓
       raw_documents
             ↓
       normalisation
             ↓
       service GPU LIDAL SLM
             ↓ sortie compacte
       compilateur déterministe V0.4
             ↓ JSON valide
       enriched_signals + FAISS + Explorateur V3
```

Le modèle ne fabrique ni offsets, ni routage, ni enveloppe JSON. Le backend les
reconstruit et valide le résultat contre le schéma V0.4. Cette séparation évite de
dépenser la capacité du modèle sur une structure calculable par code.

## 2. Station GPU Ubuntu

Cloner la branche V3 sur la station, puis pointer le service vers les poids déjà
présents dans `lidal-slm-compact` :

```bash
git clone --branch codex/lidal-pulse-v3 https://github.com/rayantr06/ramypulse.git \
  "$HOME/ramypulse-v3"
cd "$HOME/ramypulse-v3"
python -m venv .venv
.venv/bin/pip install -r requirements.txt

export LIDAL_SLM_MODEL_PATH="$HOME/lidal-slm-compact/runs/answer_only_s1"
export LIDAL_SLM_MODEL_VERSION="answer_only_s1"
export LIDAL_SLM_API_KEY="REMPLACER_PAR_UN_SECRET_LONG"

.venv/bin/uvicorn inference.slm_v04_service:app \
  --host 0.0.0.0 \
  --port 8010
```

Le service doit rester privé, idéalement accessible uniquement dans le tailnet.
Vérification locale :

```bash
curl -s http://127.0.0.1:8010/health
```

L’activation en production est interdite tant que la variante choisie n’a pas été
évaluée sur le jeu DEV et acceptée selon les portes qualité. Le simple fait que les
poids se chargent ne constitue pas une validation métier.

## 3. Backend LIDAL Pulse V3

Ajouter dans le `.env` non versionné :

```dotenv
APIFY_API_KEY=REMPLACER_PAR_LE_TOKEN_APIFY

SLM_V04_ENABLED=false
SLM_V04_BASE_URL=http://100.118.91.72:8010
SLM_V04_API_KEY=LE_MEME_SECRET_QUE_LA_STATION
SLM_V04_TIMEOUT_SECONDS=30
```

Puis installer et vérifier :

```bash
python -m pip install -r requirements.txt
python scripts/check_v3_integrations.py
```

Le diagnostic authentifie Apify sans lancer d’acteur payant et interroge seulement
`/health` pour le SLM. Il n’affiche aucun secret.

Après acceptation du modèle, passer `SLM_V04_ENABLED=true`, redémarrer le backend,
puis lancer d’abord une petite surveillance pilote. La normalisation continue à
fonctionner avec l’analyse historique si le service SLM est indisponible.

## 4. Comportement Apify

- Facebook : découverte des publications, puis collecte des commentaires ;
- Instagram : découverte des publications, puis collecte des commentaires ;
- Google Maps : recherche issue automatiquement de la marque, du produit, des
  mots-clés et des concurrents de la surveillance ;
- Google Maps conserve un repli vers Places API si Apify échoue ;
- les enveloppes historiques et les objets typés du client Apify v3 sont acceptés ;
- les données personnelles des auteurs Maps ne sont pas demandées ;
- chaque document conserve `watchlist_id`, URL source et date de publication pour
  l’audit et l’isolation multi-tenant.

Une exécution Apify peut engendrer un coût. Le bouton de création d’une surveillance
ne doit donc pas lancer plusieurs fois le même run ; le suivi existant par
`watchlist_id` et `run_id` reste obligatoire.

## 5. Contrôle pilote avant généralisation

1. créer une surveillance avec un nombre réduit de sources ;
2. vérifier le run et le nombre de `raw_documents` ;
3. contrôler le taux `validation_status=valid` ;
4. relire un échantillon français, arabe, darija arabe et arabizi ;
5. vérifier les preuves et les liens source dans l’Explorateur ;
6. comparer les KPI V2 et V0.4 sans remplacer immédiatement le dashboard stable ;
7. activer progressivement par client après validation humaine.

## 6. Retour arrière

Passer simplement `SLM_V04_ENABLED=false` et redémarrer le backend. Les annotations
V0.4 déjà stockées restent auditables ; les écrans historiques continuent grâce aux
colonnes de projection. Pour Apify, retirer `APIFY_API_KEY` force Google Maps à
utiliser Places et marque Facebook/Instagram comme sources non configurées.

## 7. Client de démonstration fondé sur le corpus DEV

La V3 peut être peuplée localement avec les 766 commentaires du jeu DEV annoté
V0.4. Le script ne publie pas le corpus et ne modifie que le tenant demandé :

```bash
python scripts/seed_training_demo.py --reset
```

Configuration locale du backend :

```dotenv
SAFE_EXPO_CLIENT_ID=demo-expo-2026
RAMYPULSE_RUNTIME_MODE=offline
```

Configuration Vite dans `frontend/client/.env.local` :

```dotenv
VITE_RAMYPULSE_DEMO_MODE=false
VITE_RAMYPULSE_DEFAULT_TENANT_ID=demo-expo-2026
VITE_RAMYPULSE_API_KEY=dev
```

Le tableau de bord, l'Explorateur, les alertes, les recommandations, les campagnes
et la surveillance utilisent alors les mêmes annotations. Les liens externes sont
des recherches publiques reconstruites depuis le contexte du corpus, car les URL
exactes des avis ne figurent pas dans le jeu DEV.
