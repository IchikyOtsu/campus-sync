# campus-sync

Application web qui centralise les horaires d’étudiants suivant des cours dans plusieurs établissements. Les intégrations passent exclusivement par l’API FastAPI : le navigateur ne contacte jamais un fournisseur d’horaires.

## Architecture

`SolidJS + TypeScript → FastAPI → PostgreSQL (Supabase en production)`.

Supabase Auth assure les comptes et émet les JWT vérifiés par l’API. Aucun mot de passe n’est stocké dans campus-sync. Le frontend est prévu pour Vercel, l’API pour Railway et la base PostgreSQL pour Supabase.

## Lancer localement

Copiez `.env.example` vers `frontend/.env` et `backend/.env`, puis renseignez les clés Supabase pour utiliser l’authentification réelle.

```bash
docker compose up --build
```

Ou séparément :

```bash
cd backend && python -m venv .venv && .venv/bin/pip install -e '.[dev]'
.venv/bin/python -m app.db.init_db
.venv/bin/uvicorn app.main:app --reload

cd frontend && npm install && npm run dev
```

L’API de santé est disponible sur `GET /health`. Le seed crée le programme ULB M-SECUC 2026–2027/Q1 et conserve les codes ULB ainsi que les codes fournisseurs correspondants. Il ne crée pas de faux horaires.

## Migrations et données

Les modèles SQLAlchemy couvrent institutions, cours, offerings, programmes/mappings, profils Supabase, PAE par année, cours du PAE, événements et changements détectés. Le backend Docker applique `alembic upgrade head` avant le seed : les anciennes sélections `user_courses` sont migrées dans les PAE correspondants. En développement, `app.db.init_db` initialise le schéma et le seed ; la migration Alembic initiale doit être générée avant le premier déploiement partagé (`alembic revision --autogenerate -m initial`).

## Tests et CI

```bash
cd backend && .venv/bin/pytest
cd frontend && npm run lint && npm run build
```

GitHub Actions exécute ces vérifications pour chaque push et pull request.

## État des connecteurs

| Provider | Institution | Statut |
| --- | --- | --- |
| ICS | Generic | Fonctionnel : fichier et URL, VEVENT, timezone et récurrences standards |
| TimeEdit | ULB | Expérimental / non connecté |
| ADE | UCLouvain | Planifié |
| ADE | UNamur | Planifié |
| Custom | HE2B | Planifié |

Un ICS importé est persisté, synchronisé par UID/external ID et alimente le calendrier ainsi que la détection des chevauchements. Les connecteurs universitaires n’effectuent aucune fausse synchronisation.

## Configuration Supabase de développement

Pour le développement sur le réseau local, configurez Supabase avec :

- Site URL : `http://192.168.0.51:5174`
- Redirect URL : `http://192.168.0.51:5174/**`

Variables frontend (dans un fichier `.env` non versionné) :

```env
VITE_API_URL=http://192.168.0.51:8000
VITE_SUPABASE_URL=https://<project>.supabase.co
VITE_SUPABASE_PUBLISHABLE_KEY=<publishable-key>
```

Variables backend :

```env
SUPABASE_URL=https://<project>.supabase.co
SUPABASE_JWT_AUDIENCE=authenticated
CORS_ORIGINS=http://192.168.0.51:5174
```

La Publishable Key est conçue pour le navigateur. Ne remplacez jamais cette clé par une clé `service_role` ou une clé secrète. L’API récupère les clés publiques JWT via le JWKS Supabase et ne reçoit pas cette Publishable Key.
