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
