# `main.py` — Line-by-Line

The entrypoint of the whole backend. Small on purpose — its only job is
to assemble everything else, not contain logic itself.

```python
from fastapi import FastAPI
```
The framework's core class.

```python
from app.routers import auth, communities, posts
```
Imports each ROUTER MODULE (the whole file, referenced as a module) —
this is what makes `auth.router`, `communities.router`, `posts.router`
accessible below. Notice: this imports the *modules*, not individual
functions — each of those files defines exactly one `router` object
that gets referenced here.

```python
app = FastAPI(title="Reddit Clone API (v3)")
```
Creates the actual application object. Every route, every piece of
middleware, everything — attaches to this one object. `title=` is
cosmetic, shows up on the auto-generated `/docs` page.

```python
app.include_router(auth.router)
app.include_router(communities.router)
app.include_router(posts.router)
```
**The most important three lines in this file.** Each router
(`auth.py`'s `/auth/signup`+`/auth/login`, `communities.py`'s
`/communities` GET+POST, `posts.py`'s nested post routes) is defined as
a standalone `APIRouter` object in its own file — on its own, a router
is just a collection of routes NOT YET connected to anything.
`include_router()` merges it into `app`, making those routes actually
reachable. **Miss one of these three lines, and that entire file's
routes would still be perfectly correct Python, and still completely
unreachable** — this is the literal wiring step.

```python
@app.get("/health")
def health_check():
    return {"status": "ok"}
```
One tiny route defined directly here rather than in its own router
file — reasonable for something this small and genuinely standalone
(not part of any resource, no DB, no auth). A simple uptime check: if
this responds, the server process is at least running.

---

## Why routers live in separate files instead of all routes being defined directly in `main.py`

Could technically write every `@app.post(...)`/`@app.get(...)` directly
in this file. Two real reasons not to:
1. **This file would grow forever** — every new feature (comments,
   votes, whatever comes later) would mean more routes piling into one
   already-large file, mixing unrelated concerns together.
2. **`APIRouter` lets each resource's routes live alongside everything
   else that resource needs** — `auth.py` has its routes right next to
   the imports it specifically needs (`hash_password`, `create_access_token`),
   `posts.py` has its routes next to its own helper
   (`_get_community_or_404`). Splitting by resource keeps each file
   self-contained and easy to find.

---

## The full picture — every router this app has, and what connects them

```
main.py
  ├── app.include_router(auth.router)         -> POST /auth/signup, /auth/login
  ├── app.include_router(communities.router)   -> GET/POST /communities
  └── app.include_router(posts.router)          -> GET/POST /communities/{id}/posts
```

All three routers depend on the same shared pieces underneath:
`db/session.py`'s `get_db()` (every route gets a DB session),
`core/deps.py`'s `get_current_user()` (every PROTECTED route uses it),
and the model/schema files each router imports directly.

**One sentence for the interview:** *"`main.py` stays intentionally thin — it just creates the FastAPI app and wires in each resource's router via `include_router()`; all the actual logic lives in the router files themselves, keeping the entrypoint readable no matter how many features get added later."*
