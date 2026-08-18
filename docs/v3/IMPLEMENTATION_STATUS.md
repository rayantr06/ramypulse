# LIDAL Pulse V3 — état d’implémentation

Date : 17 août 2026
Branche : `codex/lidal-pulse-v3`

## Résultat livré

La V3 met en œuvre le cœur du blueprint sous forme additive. La version destinée
à la vidéo reste intacte dans son autre branche/worktree.

### Contrats et expérience

- Contrats TypeScript V3 séparés dans `frontend/shared/v3.ts` ; le contrat
  historique `frontend/shared/schema.ts` n’est pas modifié.
- Navigation : Aujourd’hui, Surveillances, Signaux, Explorer, Actions, Rapports
  et Sources.
- Redirections temporaires : `/alertes` vers `/signals` et `/recommandations`
  vers `/actions`.
- Tableau de bord sans score opaque : cohorte qualifiée, sentiment net, taux
  négatif, couverture analytique, prise en charge et santé des sources.
- Création d’une surveillance en trois décisions : cible, objectif et sources.
- File de signaux avec seuil, confiance, score déterministe, preuves, validation
  humaine, faux positif et transformation en dossier.
- Dossiers et actions avec propriétaire, échéance, état, référence avant/après.
- Agent LIDAL limité aux brouillons cités ; aucune mutation ou action externe.
- Citations de l’agent typées (`metric`, `observation`, `mention`) et vérifiées
  dans l’organisation courante avant la génération du brouillon.
- États de chargement, d’erreur et de couverture absente distincts des vrais
  résultats à zéro sur les pages V3.

### Fondation plateforme

- Service FastAPI additif dans `services/v3_api/`, volontairement hors de
  `api/` pour respecter la séparation de responsabilité du dépôt.
- Référentiel pilote SQLite isolé par organisation, idempotence et journal
  d’événements.
- Migration PostgreSQL/Supabase dans
  `supabase/migrations/202608170001_lidal_pulse_v3_foundation.sql`.
- RLS explicite, vues `security_invoker`, rôles provenant de `app_metadata` et
  révocation de l’accès anonyme.
- JWT Supabase vérifié via JWKS ; l’ancien en-tête API reste une compatibilité
  interne et n’accorde pas d’autorisation métier V3.

### Collecte et analytique

- Contrat fournisseur commun : `discover → collect → normalize → checkpoint → report_cost`.
- Adaptateur Apify générique pour Facebook, TikTok et Google Maps.
- Connecteur YouTube Data API officiel.
- Limites de volume et budget avant collecte, déduplication prévue au niveau du
  dépôt et santé des sources visible dans l’interface.
- Cohorte V0.4, sentiment net avec seuil minimum de 30 mentions, priorité avec
  renormalisation des poids et détection déterministe des premiers signaux.

## Ce qui est démontrable maintenant

Le mode démonstration permet de parcourir sans service externe :

1. Aujourd’hui et ses KPI vérifiables ;
2. une surveillance avec couverture et limites ;
3. un signal et ses verbatims français, arabe et arabizi ;
4. l’ouverture d’un dossier seulement après confirmation des preuves, avec
   responsable et échéance ;
5. l’avancement d’une action, dont la résolution exige un résultat mesuré ;
6. un brouillon contrôlé de l’agent ;
7. les rapports et la santé des sources.

Les données sont explicitement signalées comme démonstration et les liens
externes utilisent un domaine non routable. Aucune performance commerciale ou
source réelle n’est inventée.

## Reste avant pilote réel

- Appliquer et valider la migration sur un projet Supabase pilote.
- Ajouter le repository PostgreSQL au service V3 (le pilote local utilise
  SQLite).
- Configurer Supabase Auth, les memberships et deux organisations de test.
- Renseigner les identifiants YouTube et Apify côté serveur, jamais dans Vite.
- Brancher le service SLM validé par les portes DEV et le compilateur V0.4.
- Ajouter les workers durables et checkpoints PostgreSQL.
- Implémenter la génération réelle des PDF/CSV et l’envoi email confirmé.
- Réaliser l’audit juridique/ANPDP avant toute donnée identifiante réelle.

## Vérifications exécutées

- `python -m pytest tests/test_v3_product_foundation.py` : 11 tests réussis,
  dont refus d’un tenant non revendiqué, d’une mutation en lecture seule,
  d’un signal sans preuve, d’un dossier non confirmé et d’une résolution sans impact.
- `npm run check` : TypeScript strict réussi.
- `npm run build` : build production réussi et pages découpées par route.
- `npm run test:quality` : contrats et contrôles UI réussis.
- `npm run test:golden` : 5 parcours E2E réussis.
- Revue visuelle desktop 1600×1200 et mobile 390×844.
- Détecteur Impeccable : aucune anomalie mécanique.

`npm run lint` n’existe pas dans le `package.json` actuel ; aucun résultat lint
ne doit donc être revendiqué.
