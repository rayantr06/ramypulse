# Architecture Orchestrateur Multi-Agent

## But

Passer d'un simple workflow Git + prompts manuels a un vrai systeme d'orchestration capable de piloter :

- un sprint complet
- une phase complete
- plusieurs agents en parallele
- des gates de validation
- des merges controles

## Recommandation

### Stack cible

- **Orchestration agentique** : OpenAI Agents SDK
- **Workflow durable** : Prefect
- **Skills repo-aware** : skills locales type OpenHands / AgentSkills
- **Execution coding** : worktrees Git + commandes locales + tests projet

### Pourquoi ce choix

- plus simple a mettre en place que `LangGraph + Temporal`
- assez solide pour orchestrer RamyPulse des maintenant
- compatible avec un repo Python local
- bon compromis entre puissance, cout de mise en oeuvre et maintenabilite

### Option enterprise plus lourde

Si le systeme grossit fortement :

- remplacer Prefect par Temporal
- garder la logique agentique
- conserver les skills repo/projet

## Ce qu'on veut orchestrer

### Niveau Sprint

Un sprint doit etre un objet executable avec :

- objectif
- branche integration cible
- agents assignes
- taches dependantes
- fichiers possedes par agent
- criteres de sortie
- commandes de verification

### Niveau Phase

Une phase doit etre un workflow compose de plusieurs sprints :

- ordre d'execution
- dependances inter-sprints
- merge progressif
- gates de qualite
- audit final de phase
- merge vers `main`

## Roles

### 1. Workflow Orchestrator

Responsabilites :

- lire la definition de phase/sprint
- creer ou verifier les branches/worktrees
- dispatcher les taches aux agents
- attendre les artefacts de sortie
- lancer les verifications
- decider `retry / fix / merge / stop`
- produire un rapport d'etat

### 2. Backend Worker

Responsabilites :

- modules Python
- TDD
- logique pure
- tests unitaires

### 3. ML Worker

Responsabilites :

- evaluation
- fine-tuning
- entity resolution avancee
- benchmarks

### 4. UI Worker

Responsabilites :

- pages Streamlit
- helpers UI testables
- smoke tests UI

### 5. Review / Audit Worker

Responsabilites :

- verifier respect PRD
- verifier respect conventions repo
- identifier risques avant merge

## Objets de workflow

### `phase.yaml`

Contient :

- id phase
- objectif
- branche integration
- sprints enfants
- gates globaux
- commande de validation finale

### `sprint.yaml`

Contient :

- id sprint
- description
- agent owner
- branche cible
- base branch
- fichiers autorises
- fichiers interdits
- tests cibles
- full suite command
- dependances
- outputs attendus

### `gate.yaml`

Contient :

- type de gate
- condition
- commande
- seuil
- action si echec

## Skills a formaliser

### Skills obligatoires

- `read_prd_section`
- `read_project_rules`
- `create_worktree`
- `tdd_cycle`
- `run_targeted_tests`
- `run_full_suite`
- `request_review`
- `merge_to_integration`
- `audit_phase`
- `cleanup_worktree`

### Skills RamyPulse specifiques

- `ramypulse-repo-conventions`
- `ramypulse-prd-gates`
- `ramypulse-performance-checks`
- `ramypulse-merge-policy`

## Workflow d'un sprint

### 1. Preparation

L'orchestrateur :

- verifie `main` ou `phaseN/integration`
- cree le worktree
- attache le bon skillset
- injecte la section PRD pertinente

### 2. Execution agent

Le worker :

- lit les contraintes
- ecrit les tests
- implemente
- verifie les tests cibles
- verifie la suite complete
- commit

### 3. Gate sprint

L'orchestrateur verifie :

- diff limite au scope
- tests cibles verts
- suite complete verte
- pas de fichiers parasites
- commit conforme

### 4. Merge integration

Si gate OK :

- merge vers `phaseN/integration`
- rerun full suite
- maj du statut sprint

## Workflow d'une phase

### 1. Initialisation

- creation de `phaseN/integration`
- chargement du manifest de phase
- lancement des sprints sans dependances

### 2. Orchestration

- paralleliser les sprints independants
- attendre les prerequis
- relancer les sprints bloques
- ouvrir automatiquement un audit intermediaire

### 3. Gate de phase

Conditions minimales :

- tous les sprints `done`
- suite complete verte
- audit final sans finding bloquant
- artefacts PRD/workflow mis a jour

### 4. Promotion vers main

- merge `phaseN/integration -> main`
- rerun full suite
- tag de phase
- publication du rapport

## Etats de workflow

Chaque sprint doit exposer un etat machine-readable :

- `draft`
- `ready`
- `running`
- `blocked`
- `needs_review`
- `ready_to_merge`
- `merged`
- `failed`

Chaque phase :

- `planning`
- `running`
- `stabilizing`
- `ready_for_main`
- `completed`

## Gates minimaux

### Gate code

- fichiers modifies conformes au scope
- aucun fichier interdit touche
- docstrings / logging / conventions respectes

### Gate tests

- tests sprint verts
- suite complete verte

### Gate produit

- respect du PRD cible
- pas de regression fonctionnelle evidente

### Gate perf

- mesure sur le point critique du sprint
- pas de degradation majeure non justifiee

## Structure repo recommandee

### Nouveau dossier

`orchestration/`

Contenu cible :

- `orchestration/phases/phase0.yaml`
- `orchestration/phases/phase1.yaml`
- `orchestration/sprints/*.yaml`
- `orchestration/gates/*.yaml`
- `orchestration/reports/`
- `orchestration/orchestrator.py`
- `orchestration/models.py`
- `orchestration/executors/`
- `orchestration/adapters/git.py`
- `orchestration/adapters/pytest.py`
- `orchestration/adapters/agents.py`

## Decoupage recommande pour RamyPulse

### Etape 1

Construire un orchestrateur local simple :

- lecture de `phase.yaml`
- lancement de sprints sequentiels ou paralleles
- suivi de statut
- merge vers integration

### Etape 2

Ajouter :

- gates automatiques
- audit automatique
- rapport markdown/json

### Etape 3

Ajouter :

- durable workflow Prefect
- reprise sur erreur
- relance selective
- notifications

## Verdict

Le workflow actuel est bon pour commencer, mais trop manuel.

La cible recommandee pour RamyPulse est :

- **OpenAI Agents SDK**
- **Prefect**
- **skills repo-aware**
- **manifests de phase/sprint**
- **1 orchestrateur central**

Ce n'est pas encore une surcouche gadget.
C'est un vrai systeme de delivery multi-agent.
