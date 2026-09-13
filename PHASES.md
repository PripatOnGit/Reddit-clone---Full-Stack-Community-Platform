# Phase-by-Phase Build Log

For each phase: **what** we built, **why**, **how**, and — specific to
this project's "keep it lean" approach — what we deliberately **scoped
out for now** (and when we'd actually need to add it back).

---

## Phase 1 — Backend scaffolding

**What we did:** set up the FastAPI project skeleton and the database
schema — **3 tables** (`users`, `communities`, `posts`) — `comments` and
`votes` were removed from scope entirely (deferred to a future project,
not even a later v3 phase; see the finalized-scope decision above). No
auth yet, no routes beyond `/health`.

Currently being **retyped file-by-file** (config.py, db/base.py,
db/session.py, the 3 models) under the "you type it, I verify + quiz
you" workflow, with a deep Q&A pass on the underlying concepts — see
`CONCEPTS.md` for the full writeups on: the backend folder structure,
why `config.py` is separate from `main.py`, why models inherit `Base`,
what Pydantic classes are, why every request gets its own DB session
(and how ACID/Postgres keeps concurrent sessions from corrupting each
other), and the full FastAPI + SQLAlchemy + psycopg2 sync stack
(including why this project uses sync, not async/await, and how FastAPI
still handles requests concurrently either way).

**Why:** every later phase needs a place to live. The schema comes first
because the models define what data the app can even represent — auth
and CRUD logic are built on top of it, not the other way around.

**How:**
- `app/core/config.py` — one `Settings` class reading `.env`.
- `app/db/base.py` + `app/db/session.py` — SQLAlchemy `Base`, `engine`,
  and `get_db()` (yields one DB session per request, always closed after).
- `app/models/*.py` — the 3 table classes (`User`, `Community`, `Post`).
- `create_tables.py` — `Base.metadata.create_all()`, run once to build
  the schema.
- `app/main.py` — `FastAPI()` instance + `/health`.

**Scoped out for now:**
- **`comments` and `votes` tables entirely** — cut from v3's scope
  (2026-09-13) to fit the 8-hour time budget and keep focus on genuinely
  understanding auth + communities/posts CRUD first. Real future work,
  not abandoned — revisit as a follow-up project once this one is solid.
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

## Phase 3a — Communities (not started)

**What:** `POST /communities` (create), `GET /communities` (list). This
is also where `core/deps.py`'s `get_current_user()` finally gets built —
deferred from Phase 2 since nothing needed it until now (creating a
community is the first action that requires knowing who's logged in).

**Scoped out for now:** pagination on the list (small, bounded dataset —
same reasoning v2 used for its `/communities` endpoint).

---

## Phase 3b — Posts (not started)

**What:** `POST /communities/{id}/posts` (create), `GET
/communities/{id}/posts` (list, with simple offset pagination —
`?page=&page_size=` built directly into this endpoint, not a separate
phase — kept lean per the 8-hour time budget).

---

**Comments and voting are OUT of v3's scope entirely** (decided
2026-09-13, to fit the 8-hour budget and keep full focus on genuinely
understanding auth + communities/posts first) — not a later v3 phase,
a separate future project once this one is solid and fully understood.

---

**Why offset, not cursor, for the pagination built into 3b:** `OFFSET`/
`LIMIT` is simpler to reason about; it gets slower at very deep pages on
very large tables (the database still scans past every skipped row), but
that cost only matters at a scale this project doesn't need to hit.
Worth being able to say exactly that in an interview, rather than
implying offset has no downsides.

---

## Phase 4 — Frontend (not started)

## Phase 5 — Testing (not started)

## Phase 6 — Docker (not started)
Planned: single-stage Dockerfile (vs. v2's multi-stage builder/runtime
split) — simpler, at the cost of a slightly larger image (build tools
stay in the final image instead of being discarded). Comes before AWS
deployment since Phase 7 runs this same `docker-compose` setup on the
EC2 instance. When we reach this phase, multi-stage will also be
explained side-by-side for comparison, even though we're only building
single-stage.

---

## Phase 7 — AWS deployment (finalized plan, not started)

**What we're building:** one EC2 instance (`t2.micro`/`t3.micro`) running
`docker-compose` (backend + frontend containers only), talking to a
separate RDS PostgreSQL instance (`db.t3.micro`) — not a containerized
Postgres. No load balancer, no ECS/Fargate, no auto-scaling.

**Why this architecture:**
- **Database on RDS, not in a container** — if the EC2 instance ever
  crashes or gets replaced, a containerized Postgres would take the data
  down with it. RDS is a separate managed service; the app server and
  the data don't share a failure point.
- **Single EC2 instance, not ECS/Fargate/ALB** — those have NO AWS free
  tier and bill continuously regardless of traffic; a single free-tier
  EC2 instance can run the whole stack directly at this scale. The
  honest limitation this accepts: no auto-restart if the instance dies,
  no auto-scaling, manual SSH-based ops — a fair, nameable tradeoff for
  this project's size, with a clear "what I'd change at scale" answer
  ready (auto-scaling group + load balancer, likely ECS).
- **No Terraform for v3** — v2 has Terraform as its IaC story; v3 stays
  plain AWS CLI/console steps, documented, so there's one less tool to
  learn while everything else is already new.

**How (planned steps, in order):**
1. Launch RDS (`db.t3.micro`, Postgres) — security group only accepts
   connections from the EC2 instance's security group, never the open
   internet (same layered-security-group idea as v2's Terraform, done
   manually here).
2. Launch EC2 (Ubuntu, `t2.micro`/`t3.micro`) — security group allows
   SSH (22, ideally locked to your own IP), HTTP (80), HTTPS (443).
3. Install Docker on the instance.
4. `git clone` the repo onto the instance directly.
5. Create a real `.env` on the server (`DATABASE_URL` pointing at the
   RDS endpoint, a real `JWT_SECRET_KEY`) — never committed to git.
6. `docker-compose up -d` — this compose file runs ONLY `backend` +
   `frontend`, not `postgres` (that's RDS now) — the one real difference
   from the local dev compose file.
7. Access via the EC2 instance's public IP directly.

**Monitoring:** default Docker logging stays as-is (nothing to change,
useful for direct SSH debugging). Additionally, configure the `awslogs`
Docker logging driver so the same log output is ALSO shipped to
CloudWatch Logs — a few lines in `docker-compose.yml`, no separate agent
to install. Add ONE CloudWatch Alarm (e.g. "notify me if the instance
stops responding"). Basic EC2/RDS CPU/memory metrics are tracked by
CloudWatch automatically, free, with no setup at all.

Docker logs vs. CloudWatch, in short: `docker logs` only exists on that
one server and disappears if it's replaced — fine for a quick check
while you're already SSH'd in. CloudWatch keeps a durable, centralized
copy that survives the server and can proactively alert you, which is
what matters when nobody's actively watching. Not either/or — CloudWatch
is purely additive on top of Docker's default logging.

**Scoped out for now:**
- **A custom domain + full HTTPS** — demo via the EC2 public IP
  directly for now. (Certbot/Let's Encrypt is cheap to add later if
  wanted — flagged as a low-cost upgrade, not required.)
- **Terraform / IaC** — plain documented CLI/console steps instead.
- **Auto-scaling, load balancer, multi-AZ RDS** — genuinely not needed
  at this project's scale; naming this as the "what I'd add at scale"
  answer is itself good interview material.

**Before creating any real AWS resources:**
1. Set an AWS Budget alert (e.g. at $1 and $5) so any unexpected cost
   triggers an email immediately.
2. Stop (don't delete) EC2/RDS when not actively demoing — a stopped
   EC2 instance doesn't bill compute hours; RDS can be stopped for up
   to 7 days at a time. Matters especially once the 12-month free tier
   window ends.
