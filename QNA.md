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
