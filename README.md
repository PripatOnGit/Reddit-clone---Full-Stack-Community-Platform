# Reddit Clone

A full-stack Reddit-style app — signup/login/logout, creating and
listing communities, creating and listing posts within a community —
built end-to-end to understand every part of it, not just have working
code.

**Stack:** FastAPI + SQLAlchemy + PostgreSQL (backend), React + Vite
(frontend).

See `CONCEPTS.md` for a running glossary of concepts covered while
building this (what each one does, why it's needed) — appended to as we
go. See `PHASES.md` for the detailed what/why/how/scoped-out log per
phase.

---

## Architecture

- **Auth:** one JWT issued on login, sent via `Authorization: Bearer`
  header on every request. No refresh token — when it expires, log in
  again. Logout is client-side only (delete the token) — there's nothing
  server-side to revoke.
- **Data model:** `users`, `communities`, `posts` only. `comments` and
  `votes` are intentionally out of scope for this project — a separate
  future project once this one is solid.
- **Pagination:** simple offset-based (`?page=&page_size=`), built
  directly into the posts-list endpoint.
- **Schema:** created directly from the models via
  `Base.metadata.create_all()` (`create_tables.py`) — no migration tool
  yet, appropriate while the schema is still taking shape.

---

## Phase log

Updated at the end of each phase — what was built, and the one or two
things worth remembering about it.

### Phase 1 — Backend scaffolding ✅
FastAPI app, the 3-table schema above, single-column indexes on foreign
keys used for filtering (`posts.community_id`). Schema created via
`create_tables.py`. Verified: models import cleanly and register all 3
tables on `Base.metadata`.

### Phase 2 — Auth (not started)
Plan: one JWT per login, sent via `Authorization: Bearer` header, no
refresh token, no rotation, no CSRF token needed (bearer-header auth
isn't vulnerable to CSRF the way cookie-based auth is — a malicious site
can't make the browser attach a custom header on its behalf). Tradeoff
being accepted: the token lives in `localStorage`, which any JavaScript
on the page can read — more exposed to XSS than a cookie-based approach
would be.

### Phase 3a — Communities ✅
Create/list communities. `get_current_user` built here (Phase 2's
deferred piece) — reads `Authorization: Bearer` header via FastAPI's
`HTTPBearer`. Verified: no token → 403 (HTTPBearer itself), bad token →
401 (our own check), valid token → 201, duplicate name → 409.

### Phase 3b — Posts (not started)
Create/list posts within a community, with simple offset pagination
built directly into the list endpoint.

### Phase 4 — Frontend (not started)

### Phase 5 — Testing (not started)

### Phase 6 — Docker (not started)
Single-stage Dockerfile — comes before AWS deployment since Phase 7
runs this same setup on the EC2 instance. Multi-stage builds explained
for comparison at this point too, even though only single-stage gets built.

### Phase 7 — AWS deployment (planned, separate session)
One EC2 instance running docker-compose (backend+frontend) + a separate
RDS PostgreSQL instance — no load balancer, no ECS/Fargate, no
Terraform. See `PHASES.md` for the full plan (architecture reasoning,
step-by-step, CloudWatch logging, and cost/budget safety steps).
