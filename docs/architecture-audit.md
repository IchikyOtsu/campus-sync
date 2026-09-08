# Audit de l’architecture existante

## État actuel

Le dépôt initial utilisait Vite avec JavaScript vanilla (`src/main.js`) et une feuille CSS unique. Il n’y avait ni SolidJS, TypeScript, API, authentification, schéma de données, tests ni Docker. Le calendrier, les cours, les conflits et la synchronisation étaient tous générés à partir de tableaux hardcodés dans le navigateur.

## Dette technique

- Aucun état ne persistait après un rechargement.
- Les données de cours et les événements présentaient des informations fictives comme si elles étaient synchronisées.
- Logique de présentation, données et interactions regroupées dans un seul module.
- Aucune frontière de sécurité entre l’utilisateur et les données d’horaire.

## Éléments conservés

L’identité visuelle (typographies, grille de semaine, cartes de cours et panneau de contexte) est conservée. Elle est déplacée dans des composants Solid et alimentée par un client API centralisé.

## Éléments remplacés

Les tableaux `courses` et `events`, les conflits calculés dans le DOM et l’état de synchronisation simulé sont supprimés. Ils sont remplacés par FastAPI, SQLAlchemy/PostgreSQL, un import ICS et le service de conflits.

## Plan de migration réalisé

1. Introduire le monorepo `frontend/` + `backend/` et Docker Compose.
2. Créer le modèle relationnel, la migration initiale et le seed M-SECUC.
3. Exposer les endpoints authentifiés et les endpoints programmes/cours/calendrier.
4. Importer et synchroniser des ICS via un connecteur normalisé.
5. Raccorder la vue semaine Solid à l’API et documenter les connecteurs non disponibles.
