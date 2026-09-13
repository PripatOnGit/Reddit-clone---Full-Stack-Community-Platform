# Q&A Log — Comprehension Checks + Expected Interview Questions

One section per file/step. Each has: the comprehension questions asked
while building it, your answer, the verdict/correction, and the
interview questions that specific piece of code tends to trigger.

---

## `app/core/config.py`

### Comprehension check

**Q1:** If you changed `access_token_expire_minutes: int = 60` to
`access_token_expire_minutes: str = 60` — what would
`type(settings.access_token_expire_minutes)` print, and would
`create_access_token()` (which does
`timedelta(minutes=settings.access_token_expire_minutes)`) still work?

> Your answer: "yes pydantic class will throw error."

**Verdict: partially right, and the actual behavior is the important
part.** Tested it directly:
- `Settings()` itself **succeeds, no error** — `.env` already has
  `ACCESS_TOKEN_EXPIRE_MINUTES=60` as text, and text matches a `str`
  field perfectly, no conversion even needed.
- The error only appears **later**, in a **different file** — when
  `timedelta(minutes="60")` actually runs inside `create_access_token()`:
  `TypeError: unsupported type for timedelta minutes component: str`.

**The lesson:** Pydantic only validates at the exact boundary you
declare. A wrong-but-still-technically-valid type (`str` accepting
`"60"`) sails straight through `Settings()`, and only breaks later,
somewhere that doesn't even mention `config.py` — turning an
immediate, obvious startup error into a confusing runtime crash. Type
hints are only as protective as how precisely you declare them.

**Q2:** Why does `database_url: str` have no default, while
`jwt_algorithm: str = "HS256"` does? What actually happens if each one
is missing from `.env`?

> Your answer: "if db url is missing, its throws error, 'something'
> will not work. if jwt algorithm is missing, by default it uses
> 'HS256' which is std algo."

**Verdict: correct.** No default = required, app refuses to start if
missing. A default = optional, silently falls back if missing.

### Expected interview questions
- "How do you manage configuration/secrets in your app, and how do
  they differ between local dev and production?"
- "What's the difference between a required and optional field in a
  Pydantic model, and why would you choose one over the other for a
  given setting?"
- "Where would `JWT_SECRET_KEY` actually come from in a real deployed
  app, versus your local `.env` file?" (→ AWS Secrets Manager /
  environment variables, from the Phase 7 deployment planning)

### Follow-up: "why is it called an ACCESS token if v3 has no refresh token?"

> Question asked: "why we need access token. this is not refresh
> token. am i right?"

**Verdict: correct** — v3 has only ONE token total, no refresh token
anywhere. The name "access token" describes its JOB (it grants access
to protected endpoints), not a contrast with a refresh token — that
two-token pattern is v2-specific.

**Why it still needs an expiry with nothing to renew it into:** since
v3 has no way to revoke one specific token early (no `refresh_tokens`
table, no session tracking), the expiry is the ONLY protection against
a stolen token — without it, a leaked token would grant access forever
(short of rotating `JWT_SECRET_KEY` and logging out every user at
once). 60 minutes is the deliberate tradeoff: no silent renewal when it
expires (must log in again), in exchange for bounding how long a
stolen token stays dangerous.

**One-liner to have ready:** *"It's called an access token because it
grants API access, not because there's a refresh token to contrast it
with — v3 deliberately has just the one, and its expiry is the only
protection against a stolen token since there's no revocation
mechanism."*

---

## `app/db/base.py`

### "How do I convince an interviewer this trivial-looking file matters?"

> Question asked: "how to covinve interviwer on this?" (re: a 3-line
> file that's just `class Base(DeclarativeBase): pass`)

**The confident one-breath answer:** *"`Base` is a shared registry point
— every model inherits from it, and that's what lets SQLAlchemy track
all of them together under `Base.metadata`. I use that in
`create_tables.py`: `Base.metadata.create_all(engine)` builds every
table that's ever inherited from this one class."* — naming the actual
file where it pays off signals real understanding, not recitation.

**The sharper follow-up to be ready for:** *"Why not just have models
inherit directly from SQLAlchemy's `DeclarativeBase`? Your `Base` adds
nothing right now."* — fair point, honest answer:

*"You're right, functionally identical right now. But having my own
`Base` subclass gives me ONE place to add shared behavior across every
model later — e.g. an automatic `created_at`/`updated_at` on every
table, or a custom `__repr__` for debugging — without touching each
model file individually. Cheap insurance policy: costs nothing now,
saves repetitive editing later."*

**One-sentence version under time pressure:** *"It's the single point
every model plugs into, so SQLAlchemy has one place to look for 'my
whole schema' — and it's where I'd add shared behavior across all
models later."*

---

## `app/db/session.py`

### "What does `yield` do?" (in `get_db()`)

> Question asked: "what yeild does?"

**Plain Python first:** `yield` PAUSES a function instead of ending it.
Calling the generator again resumes exactly where it paused, rather than
restarting from the top. Demonstrated live:
```python
def counter():
    print('before yield'); yield 1; print('after yield')
gen = counter()          # nothing runs yet
next(gen)                # prints "before yield", pauses, returns 1
next(gen)                # resumes, prints "after yield"
```

**Mapped onto `get_db()`:**
```python
def get_db():
    db = SessionLocal()
    try:
        yield db      # PAUSES here, hands db out to FastAPI
    finally:
        db.close()    # only runs once FastAPI resumes the generator
```
FastAPI: (1) calls `get_db()`, runs it to the `yield`, passes `db` into
the route function; (2) the route runs completely; (3) FastAPI resumes
the generator, running the `finally: db.close()`.

**Why `yield` and not `return db`:** `return` would END the function
immediately — no way to run cleanup code afterward. `yield` is what
makes "hand this over, wait, then come back and finish up" possible at
all — and because the cleanup is in a `finally` block, it runs even if
the route crashes with an exception.

**One-liner for the interview:** *"`get_db()` is a generator, not a
regular function — `yield` lets FastAPI hand the session to my route,
wait for the request to finish, then resume the generator to close it,
guaranteed, via the `finally` block, even on an error."*

---

## `app/models/user.py`

### "Why can't we just create tables in PostgreSQL directly? Why this `models/` folder?"

> Questions asked (across several tries before it landed): "why we
> cannot create tables in postgresql? why this model folder?" / "did
> not get this" / "doubt: what sqlalchemy's purpose?" / "how does
> sqlalchemy talks to db, what does it returns? without it, what
> happens?" / "can you explain in terms of actual req/resp?"

**What finally landed it: a live side-by-side request/response demo.**
Two throwaway FastAPI routes, same real database row, same real HTTP
requests via `TestClient`:

```python
# Route A: raw psycopg2, no SQLAlchemy, no Pydantic schema
@app.get('/without-sqlalchemy/{username}')
def get_user_raw(username: str):
    cur.execute('SELECT id, username, email, password_hash FROM users WHERE username = %s', (username,))
    row = cur.fetchone()   # a TUPLE: (1, 'priya', 'priya@example.com', 'fake_hash_for_demo')
    return {'id': row[0], 'username': row[1], 'email': row[2], 'password_hash': row[3]}  # built BY HAND

# Route B: SQLAlchemy + a Pydantic response schema (UserOut has only id/username/email)
@app.get('/with-sqlalchemy/{username}', response_model=UserOut)
def get_user_orm(username: str):
    user = db.query(User).filter(User.username == username).first()  # a real User OBJECT
    return user   # FastAPI + the schema build the JSON automatically
```

**Actual output:**
```
GET /without-sqlalchemy/priya
{'id': 1, 'username': 'priya', 'email': 'priya@example.com', 'password_hash': 'fake_hash_for_demo'}
   ^^^ password_hash LEAKED into the real HTTP response, live, in this exact demo

GET /with-sqlalchemy/priya
{'id': 1, 'username': 'priya', 'email': 'priya@example.com'}
   ^^^ password_hash CANNOT appear -- UserOut never declared that field
```

**The actual answers, now concrete:**
- **How does SQLAlchemy talk to the DB?** Still via psycopg2 underneath
  — same connection, same SQL sent over the wire. SQLAlchemy sits ON
  TOP of psycopg2, it doesn't replace it.
- **What does it return?** A real Python object (`User`, with named
  attributes `.id`/`.username`/`.email`) instead of an anonymous tuple
  where you must remember column *position* by hand.
- **Without it, what happens?** You get tuples everywhere, forever, and
  you build every API response dict BY HAND — which is exactly how
  `password_hash` leaked in Route A above. Not hypothetical: it just
  happened, live, because building a response dict manually is
  genuinely easy to get wrong.
- **In terms of req/resp specifically:** the DB layer (SQLAlchemy vs.
  raw SQL) determines what shape of data you're holding INSIDE the
  route (object vs. tuple). The response schema (`UserOut`) determines
  what actually gets serialized into the OUTGOING response body — and
  that's the layer that structurally prevents a field from ever
  appearing, rather than relying on a developer remembering to exclude
  it every single time.

**One-liner for the interview:** *"SQLAlchemy still uses psycopg2 under
the hood — the difference is it gives me back real objects with named
fields instead of raw tuples, and paired with a Pydantic response
schema, sensitive fields like `password_hash` structurally can't leak
into an API response, because the schema simply never lists them."*

---

## `app/routers/auth.py`

### Q1: Why one query with `|` (OR) instead of two separate queries for username/email?

> Your answer: not sure

**Answer: performance, specifically network round trips.** Every
`db.query(...)` call is psycopg2 sending SQL over the network to
Postgres and BLOCKING until a response comes back (see the sync-stack
entry above). Two separate queries = two full round trips. One combined
query (`(User.username == x) | (User.email == y)`) checks both
conditions in ONE round trip — Postgres evaluates the `OR` itself in a
single `SELECT ... WHERE username = ? OR email = ?`. Matters more as the
DB gets busier or has real network latency (e.g. a real deployed app
where the DB isn't on the same machine as the app).

### Q2: Why does `login()` return the identical 401 message whether the username doesn't exist OR the password is wrong?

> Your answer: not sure

**Answer: prevents username enumeration.** If "no such user" and "wrong
password" were different messages, an attacker could send login
attempts with different usernames and learn WHICH ones are real
accounts just from which error comes back — without ever guessing a
correct password. One identical message for both cases closes that leak
entirely.

**One-liner for the interview (covers both):** *"I combined the
username/email uniqueness check into one query to minimize DB round
trips, and I return the same error message for 'no such user' and
'wrong password' specifically to avoid leaking which usernames exist to
an attacker (username enumeration)."*
