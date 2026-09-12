# Reddit Clone

A full-stack Reddit-style app — users, communities, posts, comments,
and voting — built end-to-end to understand every part of it, not just
have working code.

**Stack:** FastAPI + SQLAlchemy + PostgreSQL (backend), React + Vite
(frontend).

See `CONCEPTS.md` for a running glossary of concepts covered while
building this (what each one does, why it's needed) — appended to as we
go.

---

## Architecture

- **Auth:** one JWT issued on login, sent via `Authorization: Bearer`
  header on every request. No refresh token — when it expires, log in
  again.
- **Data model:** `users`, `communities`, `posts`, `comments` (flat for
  now, no nested replies), `votes` (**posts only** for now — one user
  can vote once per post, value -1 or 1).
- **Pagination:** simple offset-based (`?page=&page_size=`).
- **Schema:** created directly from the models via
  `Base.metadata.create_all()` (`create_tables.py`) — no migration tool
  yet, appropriate while the schema is still taking shape.

---

## Phase log

Updated at the end of each phase — what was built, and the one or two
things worth remembering about it.

### Phase 1 — Backend scaffolding ✅
FastAPI app, the 5-table schema above, single-column indexes on foreign
keys used for filtering (`posts.community_id`, `comments.post_id`).
Schema created via `create_tables.py`.

### Phase 2 — Auth (in progress)
Plan: one JWT per login, sent via `Authorization: Bearer` header, no
refresh token, no rotation, no CSRF token needed (bearer-header auth
isn't vulnerable to CSRF the way cookie-based auth is — a malicious site
can't make the browser attach a custom header on its behalf). Tradeoff
being accepted: the token lives in `localStorage`, which any JavaScript
on the page can read — more exposed to XSS than a cookie-based approach
would be. Logout is client-side only (delete the token) — there's
nothing for the server to revoke.

### Phase 3a — Communities (not started)
Create/list communities. This is also where `get_current_user` gets
built — deferred from Phase 2 since nothing needed it until now.

### Phase 3b — Posts (not started)
Create/list posts within a community.

### Phase 3c — Comments (not started)
Flat comments (create/list) on a post — no nested replies for now.

### Phase 3d — Voting (not started)
Posts only for now — simpler `votes` table (no nullable `comment_id`,
no check constraint, just one plain unique constraint on
`(user_id, post_id)`). Comment voting can be added later as its own
small phase.

### Phase 4 — Pagination (not started)
Simple offset-based (`?page=&page_size=`), added once posts/comments
exist to paginate.

### Phase 5 — Frontend (not started)

### Phase 6 — Testing (not started)

### Phase 7 — Docker (not started)
Single-stage Dockerfile — comes before AWS deployment since Phase 8
runs this same setup on the EC2 instance.

### Phase 8 — AWS deployment (planned, not started)
One EC2 instance running docker-compose (backend+frontend) + a separate
RDS PostgreSQL instance — no load balancer, no ECS/Fargate, no
Terraform. See `PHASES.md` for the full plan (architecture reasoning,
step-by-step, CloudWatch logging, and cost/budget safety steps).
