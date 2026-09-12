# Phase-by-Phase Build Log

For each phase: **what** we built, **why**, **how**, and — specific to
this project's "keep it lean" approach — what we deliberately **scoped
out for now** (and when we'd actually need to add it back).

---

## Phase 1 — Backend scaffolding

**What we did:** set up the FastAPI project skeleton and the database
schema — 5 tables (`users`, `communities`, `posts`, `comments`, `votes`),
no auth, no routes beyond `/health`.

**Why:** every later phase needs a place to live. The schema comes first
because the models define what data the app can even represent — auth
and CRUD logic are built on top of it, not the other way around.

**How:**
- `app/core/config.py` — one `Settings` class reading `.env`.
- `app/db/base.py` + `app/db/session.py` — SQLAlchemy `Base`, `engine`,
  and `get_db()` (yields one DB session per request, always closed after).
- `app/models/*.py` — the 5 table classes. `votes` uses one table for
  both post- and comment-votes, guarded by a DB check constraint
  (exactly one target, value -1 or 1) and partial unique indexes
  (one vote per user per target).
- `create_tables.py` — `Base.metadata.create_all()`, run once to build
  the schema.
- `app/main.py` — `FastAPI()` instance + `/health`.

**Scoped out for now:**
- **Alembic** (migrations) — no real data yet to preserve across schema
  changes, so `create_tables.py` is enough. Add Alembic back the moment
  there's real user data that a schema change could destroy.
- **Composite indexes** (e.g. `(community_id, created_at)`) — v2 needed
  these specifically for cursor pagination; v3 uses simple offset
  pagination, so plain single-column indexes on the foreign keys are
  enough for now.

---

## Phase 2 — Auth (in progress)

**What we're doing:** one JWT issued on login, sent back on every
request via `Authorization: Bearer <token>`. No refresh token, no
rotation, no session tracking table.

**Why:** the goal is a version of auth simple enough to explain
completely, not the deepest possible version. One token means one
"is this valid" check everywhere — no rotation logic, no revocation
table, no CSRF token to reason about (see below).

**How (planned):**
- `app/core/security.py` — `hash_password()`, `verify_password()`
  (bcrypt), `create_access_token()`, `decode_token()` (JWT sign/verify).
- `app/schemas/user.py` — `UserCreate`, `UserOut`.
- `app/schemas/token.py` — `LoginRequest`, `TokenResponse`.
- `app/routers/auth.py` — `POST /auth/signup`, `POST /auth/login` only.

**Scoped out for now:**
- **`core/deps.py` / `get_current_user()`** — not needed until the first
  *protected* route exists (Phase 3's "create a post" needs to know who
  the author is; signup/login don't need to check identity, they
  establish it). Building it now would mean unused code sitting around
  with nothing calling it yet — added right when Phase 3 needs it instead.
- **Refresh tokens / rotation** — a deliberate v3-wide simplification.
  Consequence accepted: once the access token expires (60 min), the user
  must log in again; no silent renewal.
- **CSRF protection** — not needed at all with this design. CSRF exploits
  the browser auto-attaching *cookies*; a bearer token in a header is
  only ever attached by our own JS, which a malicious third-party page
  can't forge. This isn't "scoped out," it's genuinely unnecessary here.
- **`/auth/logout` endpoint** — nothing for the server to revoke with no
  session table; logout is 100% client-side (delete the token from
  `localStorage`).

---

## Phase 3 — CRUD + pagination (not started)

**What:** communities/posts/comments/votes endpoints, simple offset
pagination (`?page=&page_size=`). This is also where `get_current_user`
finally gets built, at the exact point a route needs it.

**Scoped out for now (anticipated):**
- Redis caching, rate limiting — senior/scale concerns, not part of v3's
  goal.

---

## Phase 4 — Frontend (not started)

## Phase 5 — Testing (not started)

## Phase 6 — Docker (not started)
Planned: single-stage Dockerfile (vs. v2's multi-stage builder/runtime
split) — simpler, at the cost of a slightly larger image (build tools
stay in the final image instead of being discarded).
