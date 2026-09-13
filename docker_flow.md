# Docker Flow — Single-Stage Build, Run, Verify, and the Multi-Stage Comparison

Read alongside `backend/Dockerfile`.

---

## What problem Docker solves (recap)

Right now the app runs because of a very specific setup on one laptop:
Python 3.13, a `.venv` with exact package versions, PostgreSQL as a
Windows service, `.env` values. Docker packages the app together with
everything it needs into one self-contained unit, so it behaves
identically on any machine.

**Image** = a frozen, built snapshot (a template). **Container** = a
running instance of an image. **Dockerfile** = the recipe that produces
an image.

---

## `backend/Dockerfile` — line-by-line (single-stage)

```dockerfile
FROM python:3.13-slim
```
Start from an official image that already has Python 3.13 installed on
a minimal Linux base. `-slim` = smaller than the full default image,
without the sometimes-quirky `alpine` variant's C-library differences.

```dockerfile
WORKDIR /app
```
Sets `/app` as the working directory for every instruction after this
— like `cd /app`, and creates the folder if needed.

```dockerfile
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
```
Copy ONLY the dependency list first, then install. **Why not copy
everything at once:** Docker caches each instruction as a layer, reused
if its inputs haven't changed. Copying all code first would mean ANY
code change invalidates the cache for `pip install` too, forcing a slow
reinstall every time. Copying `requirements.txt` alone means editing
app code later never re-triggers this expensive step.

```dockerfile
COPY app ./app
COPY create_tables.py .
```
Now copy the actual application code.

```dockerfile
EXPOSE 8000
```
Documentation only — does NOT make the port reachable. That's a
separate step (`-p` on `docker run`, or `ports:` in compose).

```dockerfile
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```
The command that runs when a container starts. List form (not a plain
string) runs `uvicorn` as the container's main process directly —
matters for how Docker delivers stop signals cleanly. `--host 0.0.0.0`
is required — the default `127.0.0.1` would only accept connections
from inside the container itself.

---

## The full build → run → verify → cleanup cycle

### 1. Build
```bash
docker build -t v3-backend-single-stage .
```
`-t` tags (names) the resulting image. `.` is the **build context** —
"use this directory as the source for any `COPY` instructions," which
is why you run this from inside `backend/`.

**What happens:** each Dockerfile instruction becomes a numbered step
(`[1/6]`...`[6/6]`), executed top to bottom.

### 2. Run
```bash
docker run -d --name v3-backend-test -p 8001:8000 \
  -e DATABASE_URL="postgresql://postgres:postgres@host.docker.internal:5432/reddit_clone_v3" \
  -e JWT_SECRET_KEY="test-secret-for-docker-demo" \
  v3-backend-single-stage
```
- `-d` — detached (background)
- `--name` — a friendly name for this running container
- `-p 8001:8000` — publish container port 8000 to host port 8001 (host:container) — THIS is what actually makes it reachable, unlike `EXPOSE`
- `-e KEY=value` — inject environment variables AT RUNTIME, not baked into the image — how `core/config.py`'s `Settings` gets its values here, with no `.env` file inside the container at all
- **`host.docker.internal`** — a container is an isolated environment; `localhost` inside it means the container itself, not your Windows machine. Docker Desktop provides this special hostname specifically to reach back out to the host machine (needed here since Postgres runs natively on Windows, not in a container).

### 3. Verify — three levels of proof, each stronger

```bash
docker ps --filter "name=v3-backend-test"      # is it even running
curl http://localhost:8001/health               # does the app respond at all
curl -X POST http://localhost:8001/auth/signup -d '{...}'   # does the FULL stack work
psql -U postgres -h localhost -d reddit_clone_v3 -c "SELECT * FROM users;"  # verify from OUTSIDE docker entirely
```
The last one is the strongest proof — it verifies data really persisted, checked from a tool that has nothing to do with Docker at all, not just the container claiming success.

### 4. Clean up
```bash
docker stop v3-backend-test
docker rm v3-backend-test
```
**Important distinction:** this removes the CONTAINER, not the image.
`v3-backend-single-stage` (the image) still exists afterward — you'd
need `docker rmi` to remove that. Same image → container relationship
as always: many containers can come and go from one persisting image.

---

## Interview demo script (condensed)

1. `docker --version` / `docker ps` — Docker itself is running
2. `docker images v3-backend-single-stage` (or build live) — the image exists
3. `docker run ...` — start a real container
4. `docker ps` — confirm it's running, point at the port mapping
5. `curl .../health` — proves it's actually serving requests
6. `curl -X POST .../auth/signup` + a direct `psql` query — strongest proof: real end-to-end work, verified independently of Docker
7. `docker stop && docker rm` — clean up

**Opening line:** *"Let me show the whole lifecycle — build the image, run a container from it, then prove it's serving real requests against the real database, not just that the process started."*

---

## Single-stage vs. multi-stage — the HONEST comparison (not just theory)

Built v2's actual multi-stage Dockerfile and compared real sizes:

| | Single-stage (v3) | Multi-stage (v2) |
|---|---|---|
| Disk usage | 335MB | 335MB |
| Content size | 79.8MB | 79.2MB |

**Nearly identical — genuinely surprising if you expect multi-stage to
always win on size.** Here's the honest reason why, worth being able to
explain rather than reciting "multi-stage is always smaller":

Multi-stage's size benefit comes from **discarding build-time-only
baggage** that a runtime doesn't need — most classically, a C compiler
and dev headers needed to build a Python package with native
extensions (e.g. some packages need `gcc` to compile a C extension
during `pip install`, and that compiler is dead weight afterward).
**This project's dependencies are all pure-Python or ship prebuilt
wheels** (FastAPI, SQLAlchemy, psycopg2-binary — note the `-binary`
suffix, which means precompiled, no compiler needed) — so there's
nothing bulky being left behind either way. Multi-stage's `--prefix=/install`
trick mainly avoids pip's *download cache*, which `--no-cache-dir`
already strips in the single-stage version too.

**Where multi-stage genuinely still wins here — security, not size:**
v2's Dockerfile adds `RUN useradd --create-home appuser` + `USER appuser`
— running as a non-root user inside the container. v3's single-stage
version runs as root (Docker's default) inside the container. If the
app were ever compromised, root-inside-the-container gives an attacker
more to work with than a restricted user would. This is a real,
independent decision from single-vs-multi-stage — you could add a
non-root user to a single-stage Dockerfile too — but it happens to be
present in v2's multi-stage version and absent from v3's simpler one.

**The honest interview answer:** *"I tested this — for this project specifically,
multi-stage and single-stage produced nearly identical image sizes,
because none of our dependencies need compiling from source. Multi-stage's
real size win shows up when a package needs build tools (a C compiler,
dev headers) that aren't needed at runtime — that's not the case here.
The genuine difference in this codebase is that v2's Dockerfile also
runs as a non-root user, which is a security improvement independent
of the staging question."*

This is a stronger answer than "multi-stage is always better" — it
shows you actually measured it rather than repeating received wisdom.
