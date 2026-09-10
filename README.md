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
- **Data model:** `users`, `communities`, `posts`, `comments` (with
  nested replies via `parent_comment_id`), `votes` (one table for both
  post and comment votes, with a DB check constraint enforcing exactly
  one target and a value of -1 or 1, plus partial unique indexes so a
  user can't vote twice on the same target).
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

### Phase 3 — CRUD + pagination (not started)

### Phase 4 — Frontend (not started)

### Phase 5 — Testing (not started)

### Phase 6 — Docker (not started)
