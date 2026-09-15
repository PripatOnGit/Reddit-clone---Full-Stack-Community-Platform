# Reddit Clone

A full-stack Reddit-style community platform — signup/login, creating
and browsing communities, and creating and browsing posts within a
community, with pagination.

**Stack:** FastAPI + SQLAlchemy + PostgreSQL (backend), React + Vite
(frontend), Docker + docker-compose.

---

## Features

- JWT-based authentication (signup, login) via `Authorization: Bearer`
- Create and list communities
- Create and list posts within a community, with offset-based pagination
- Fully containerized: backend, frontend, and PostgreSQL each run as
  their own Docker container, orchestrated with `docker-compose`

## Architecture

- **Auth:** one JWT issued on login, sent via `Authorization: Bearer`
  header on every request. No refresh token — when it expires, the
  user logs in again. Logout is client-side only (the token is deleted
  from the browser) — there is no server-side session to revoke.
- **Data model:** `users`, `communities`, `posts`. Foreign-key and
  uniqueness constraints (e.g. one community per name) are enforced at
  the database level, not just in application code.
- **Pagination:** offset-based (`?page=&page_size=`) on the posts-list
  endpoint, returning `items`, `total`, `page`, and `page_size` so a
  client can compute total pages.
- **Schema management:** the database schema is created directly from
  the SQLAlchemy models (`create_tables.py`), rather than via a
  migration tool.

## API

| Method | Path | Auth required |
|---|---|---|
| POST | `/auth/signup` | No |
| POST | `/auth/login` | No |
| GET | `/communities` | No |
| POST | `/communities` | Yes |
| GET | `/communities/{id}/posts?page=&page_size=` | No |
| POST | `/communities/{id}/posts` | Yes |
| GET | `/health` | No |

## Running locally

**With Docker (recommended):**
```bash
docker compose up --build
```
This starts PostgreSQL, the backend (`http://localhost:8000`), and the
frontend (`http://localhost:5175`) together, creating the database
schema automatically on startup.

**Without Docker** (requires a local PostgreSQL instance):
```bash
# backend
cd backend
python -m venv .venv && .venv/Scripts/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in DATABASE_URL / JWT_SECRET_KEY
python create_tables.py
uvicorn app.main:app --reload

# frontend, in a separate terminal
cd frontend
npm install
npm run dev
```

## Project status

- [x] Backend scaffolding (schema, models)
- [x] Authentication (signup/login)
- [x] Communities (create/list)
- [x] Posts (create/list, with pagination)
- [x] Frontend
- [x] Docker (backend, frontend, and docker-compose)
- [ ] AWS deployment (EC2 + RDS) — planned, not yet live
