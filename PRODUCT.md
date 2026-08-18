# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

L'utilisateur prioritaire de la première version est le responsable marketing, communication ou direction qui doit comprendre rapidement ce qui change dans les retours clients et décider quoi faire. Les responsables qualité et expérience client remontent aux preuves et priorisent les corrections. Les analystes explorent les signaux, filtres et verbatims à plus forte densité. Les opérateurs administrent les sources, connecteurs et exécutions de collecte dans une console distincte.

## Product Purpose

LIDAL Pulse transforme des commentaires, avis et signaux publics, autorisés ou fournis par une organisation en observations quantifiées, signaux vérifiables, dossiers attribués et actions mesurables. Le produit réduit le délai entre l'apparition d'un changement client, la preuve qui le justifie et une décision que l'organisation peut réellement exécuter.

Le parcours métier prioritaire est : Aujourd’hui → Mention → Observation → Signal → Dossier → Action → Impact.

## Positioning

LIDAL Pulse relie chaque conclusion à ses verbatims et à sa provenance, avec une compréhension adaptée au français, à l'arabe, à la darija, à l'arabizi et au code-switching algérien. Sa valeur n'est pas un score de sentiment isolé, mais une chaîne vérifiable allant du signal brut à une décision opérationnelle.

## Operating Context

Le produit est utilisé comme plateforme de veille continue et lors de l'analyse ponctuelle d'une marque, d'un produit, d'une campagne, d'un concurrent ou d'un risque. Un utilisateur sélectionne un espace client, configure une surveillance en trois décisions, suit la couverture et la fraîcheur, vérifie les signaux et leurs preuves, ouvre un dossier, assigne une action, puis mesure l'impact avant/après.

## Capabilities and Constraints

- Frontend existant : React 18, Vite 7, TypeScript strict, Tailwind CSS, Shadcn/Radix, TanStack Query, Wouter, Recharts et Framer Motion.
- Architecture multi-tenant avec isolation par espace client.
- Vues V3 : Aujourd’hui, Surveillances, Signaux, Explorer, Actions, Rapports et Sources. Campagnes reste compatible après le cœur métier.
- Les contrats API, comportements fonctionnels, routes et `data-testid` nécessaires aux tests doivent être préservés.
- Le SLM V2 et son corpus contrôlé sont en développement et ne doivent pas être présentés comme validés en production.
- Les sources, la fraîcheur, la confiance et les limites d'une conclusion IA doivent rester visibles.
- L'interface doit supporter les contenus français, arabes, darija, arabizi et mixtes, avec une future interface RTL.
- L'administration technique doit rester séparée de l'usage métier.

## Brand Commitments

- LIDAL AI est la structure porteuse ; LIDAL Pulse est le nom du produit.
- RamyPulse est l'ancien nom du prototype et ne doit plus être présenté comme la marque produit générale.
- Le Groupe Ramy est un pilote potentiel ayant exprimé un intérêt et autorisé sa citation ; il ne doit pas être présenté comme un client acquis ou un contrat signé.
- La nouvelle identité est claire en priorité et remplace l'univers noir et pêche du prototype au lieu de le recolorer superficiellement.
- Aucun ancien symbole RamyPulse n'est obligatoire pour la nouvelle identité.

## Evidence on Hand

- Prototype fonctionnel et frontend dans `frontend/`.
- Documentation produit et candidature ProtoMarket dans `docs/` et `docs/protomarket_ii_2026/`.
- Brochure historique dans `docs/LIDAL_AI_RamyPulse_Brochure (3).docx`.
- Corpus, collectes et données de démonstration présents localement dans `data/`.
- Le dépôt contient des exemples de parcours, tests E2E et captures visuelles ; aucune métrique commerciale, validation de production ou relation client supplémentaire ne doit être inventée.

## Product Principles

1. Montrer la preuve avant de demander la confiance.
2. Transformer les signaux validés en dossiers et actions mesurables, pas seulement en graphiques.
3. Rendre la complexité progressive : synthèse pour le décideur, profondeur pour l'analyste.
4. Employer un langage métier clair et expliquer les limites de l'IA.
5. Concevoir pour le contexte linguistique algérien sans folklore visuel.

## Accessibility & Inclusion

Le produit vise WCAG 2.2 AA : contraste, clavier, focus visible, tailles tactiles, graphiques compréhensibles sans dépendre uniquement de la couleur et respect de `prefers-reduced-motion`. Les textes arabes et mixtes doivent conserver une lecture correcte, et l'architecture doit permettre une future interface RTL.
