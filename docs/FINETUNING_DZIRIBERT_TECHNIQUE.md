# Fine-tuning DziriBERT — Document technique

**Version :** 1.0  
**Date :** 2026-03-28  
**Statut :** Référence technique Phase 0  
**Classification :** Interne — Technique

---

## Contexte

Ce document contient les hyper-paramètres et détails techniques du fine-tuning DziriBERT, extraits du PRD v6 pour maintenir la séparation PRD / spécification technique.

Le plan d'action stratégique (seuils F1, alternatives, effort estimé) reste dans le PRD §7.1.2.

---

## Hyper-paramètres recommandés

| Paramètre | Valeur recommandée | Notes |
|-----------|-------------------|-------|
| `learning_rate` | 2e-5 | Standard pour BERT fine-tuning |
| `epochs` | 5 | À ajuster selon la convergence |
| `batch_size` | 16 | Réduire à 8 si contrainte mémoire GPU |
| `warmup_ratio` | 10% | Warmup linéaire |
| `weight_decay` | 0.01 | Régularisation standard |
| `max_seq_length` | 128 | Suffisant pour les retours consommateurs courts |
| `fp16` | True | Si GPU compatible, sinon fp32 |
| `gradient_accumulation_steps` | 1 | Augmenter si batch_size réduit |

---

## Procédure

1. **Modèle de base** : DziriBERT pré-entraîné (`alger-ia/dziribert`)
2. **Tâche** : Classification de séquence (5 classes discrètes)
3. **Classification head** : Linear(768, 5) — remplace la tête existante
4. **Optimizer** : AdamW
5. **Scheduler** : Linear warmup + linear decay
6. **Environnement** : Local uniquement (pas de fine-tuning cloud)

---

## Dataset

- Minimum 3 000 exemples annotés en 5 classes
- Répartition équilibrée entre les classes
- Sources : Facebook, Google Maps, forums, SAV
- Split : 80% train / 20% test
- Inter-annotator agreement cible : ≥ 0.65 (Cohen's kappa)

---

## Évaluation

| Métrique | Seuil MVP (Phase 0) | Seuil cible (Phase 2+) |
|----------|---------------------|------------------------|
| F1 macro | ≥ 0.70 | ≥ 0.80 |
| F1 par classe | ≥ 0.60 chaque classe | ≥ 0.70 chaque classe |
| Accuracy | ≥ 0.65 | ≥ 0.75 |
| Dataset test | ≥ 600 exemples | ≥ 1000 exemples |

---

## Alternatives en cas d'échec

Si DziriBERT ne converge pas (F1 < 0.60 après 3 runs) :

1. **CAMeLBERT** — BERT pré-entraîné sur l'arabe dialectal
2. **MarBERT** — BERT pré-entraîné sur Twitter arabe
3. **ArabBERT** — BERT pré-entraîné sur l'arabe standard

---

*Ce document accompagne le PRD Post-Wave 4 v6 (§7.1.2).*
