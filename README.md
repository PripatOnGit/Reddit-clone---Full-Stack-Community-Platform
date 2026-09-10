# Reddit Clone (v3) — Toned-Down Rebuild

A simpler rebuild of the Reddit Clone project, built to genuinely
understand every part of it end-to-end — not just have working code.
`v2` (in the sibling folder) stays untouched as an advanced/senior-depth
reference; this is the active build going forward.

**Why this exists:** after building v2 (JWT rotation, absolute session
caps, httpOnly cookies + CSRF, cursor pagination, multi-stage Docker,
Redis caching), it became clear those concepts were layered on faster
than they were sinking in. v3 rebuilds the same core app with the three
most advanced pieces deliberately simplified, so every line is something
that can be explained confidently, not just recited.

**Stack:** FastAPI + SQLAlchemy + PostgreSQL (backend), React + Vite
(frontend). No Alembic (see `CONCEPTS.md`), no Redis, single-stage Docker.

See `CONCEPTS.md` for a running glossary of concepts covered as we build
(what each one does, why we need it — appended to as we go, not replaced).

---

## What's simplified vs. v2, and why

| | v2 | v3 |
|---|---|---|
| Auth | Access+refresh JWT, rotation, absolute session cap, httpOnly cookies, CSRF double-submit | One JWT, `Authorization: Bearer` header, no rotation |
| Pagination | Cursor-based (`created_at, id`) | Simple offset (`?page=&page_size=`) |
| Schema migrations | Alembic | `Base.metadata.create_all()` (schema still taking shape) |
| Docker | Multi-stage builder/runtime | Single-stage |
| Caching / rate limiting | Redis cache-aside, in-memory rate limiter | Not included (senior/scale concerns, out of scope for v3) |

---

## Phase log

Updated after each phase completes — what was built, and the one or two
things worth remembering about it.

### Phase 1 — Backend scaffolding ✅
FastAPI app, same 5-entity schema as v2 (users, communities, posts,
comments, votes) but **no `refresh_tokens` table** — nothing to track
without rotation. Single-column indexes (`ix_posts_community_id`)
instead of v2's composite `(community_id, created_at)` index, since that
composite existed specifically to serve cursor pagination.

Schema created via `create_tables.py` (`Base.metadata.create_all()`),
no Alembic — see `CONCEPTS.md`.

### Phase 2 — Simplified auth (in progress)
Plan: one JWT per login, sent via `Authorization: Bearer` header, no
refresh token, no rotation, no CSRF token needed (bearer-header auth
isn't vulnerable to CSRF the way cookie auth is — a malicious site can't
make the browser attach a custom header on its behalf). Tradeoff being
accepted: the token lives in `localStorage`, which is more exposed to
XSS than v2's httpOnly cookies were. Logout is client-side only (delete
the token) — there's nothing for the server to revoke.

### Phase 3 — CRUD + simple pagination (not started)

### Phase 4 — Frontend (not started)

### Phase 5 — Testing (not started)

### Phase 6 — Docker (not started)
