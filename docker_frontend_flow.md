# Docker Frontend Flow — Line-by-Line, Build/Run/Verify, and the Real Multi-Stage Win

Read alongside `frontend/Dockerfile`. Companion to `docker_flow.md`
(the backend's Docker story) — this is where multi-stage's size benefit
actually shows up dramatically, unlike the backend.

---

## `frontend/Dockerfile` — line-by-line (single-stage)

```dockerfile
FROM node:20-slim
```
Start from an official image with Node.js 20 already installed, on a
minimal Linux base.

```dockerfile
WORKDIR /app
```
Same as the backend — sets the working directory for everything after.

```dockerfile
COPY package.json package-lock.json ./
RUN npm ci
```
Copy ONLY the dependency manifests first (same layer-caching reasoning
as the backend's `requirements.txt` trick — code changes later won't
force a reinstall). `npm ci` (not `npm install`): installs EXACTLY what
`package-lock.json` specifies, deletes `node_modules` first if it
exists, and fails outright if the lockfile and `package.json` are out
of sync — deterministic and reproducible, unlike `npm install` which
can silently update the lockfile.

```dockerfile
COPY . .
RUN npm run build
```
Copy the rest of the source (`src/`, `index.html`, etc.), then run
Vite's production build — bundles and minifies everything into static
HTML/CSS/JS inside `/app/dist`.

```dockerfile
RUN npm install -g serve
```
Installs a tiny static file server globally inside the image — this is
what will actually serve the built files.

```dockerfile
EXPOSE 80
```
Documentation only, same as always — doesn't make anything reachable
by itself.

```dockerfile
CMD ["serve", "-s", "dist", "-l", "80"]
```
The command that runs when a container starts: serve the `dist/`
folder (the built output from `npm run build`) on port 80. `-s` =
single-page-app mode (routes unknown paths back to `index.html` — not
strictly needed here since there's no client-side router, but
harmless).

---

## Build → Run → Verify (same cycle as the backend)

```bash
docker build -t v3-frontend .
docker run -d --name v3-frontend-test -p 5176:80 v3-frontend
curl -o /dev/null -w "status: %{http_code}\n" http://localhost:5176
# -> status: 200
docker stop v3-frontend-test && docker rm v3-frontend-test
```
Same pattern as the backend's cycle in `docker_flow.md`: build the
image, run a container with a port mapping, verify with a real request,
clean up the container (not the image).

---

## The real multi-stage win — measured, not theoretical

Built v2's actual multi-stage frontend Dockerfile and compared:

| | v3 single-stage | v2 multi-stage |
|---|---|---|
| Disk usage | **530MB** | **102MB** |
| Content size | 140MB | 28.9MB |

**Roughly 5x smaller with multi-stage — a dramatic, real difference**,
unlike the backend where single- and multi-stage came out nearly
identical. Here's v2's actual Dockerfile, and why this case is
different:

```dockerfile
# --- stage 1: build the static assets ---------------------------------------
FROM node:20-slim AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build   # outputs to /app/dist

# --- stage 2: serve the built static files with nginx ------------------------
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
```

**Why this one genuinely shrinks so much:** the FIRST stage needs all
of Node.js, npm, and every package in `node_modules` (React, Vite, and
all of Vite's own build tooling) just to *produce* the built files —
but once `npm run build` finishes, none of that is needed to actually
*serve* those files. The second stage throws ALL of it away and starts
completely fresh from `nginx:alpine` (a tiny web server, not even
Node-based), copying in ONLY the finished `dist/` folder — a handful of
HTML/CSS/JS files.

**Contrast directly with why the backend case was different (see
`docker_flow.md`):** the backend's dependencies (FastAPI, SQLAlchemy,
psycopg2-binary) are all needed to actually RUN the app, not just to
build it — there's no equivalent "build vs. runtime" split to exploit.
The frontend has an unusually clean split: a heavy toolchain to
*produce* static files, then literally nothing but a webserver needed
to *serve* them.

**The honest, complete interview answer, covering both cases:**
*"I measured multi-stage's benefit on both halves of this project. For
the backend, single- and multi-stage came out nearly identical, since
none of the dependencies need compiling. For the frontend, multi-stage
cut the image size by about 5x, because the entire Node/npm/build
toolchain is only needed to PRODUCE the static files, not to SERVE
them — the final stage can be a totally different, much smaller base
image (nginx) with none of that toolchain at all. Multi-stage's payoff
depends entirely on whether there's a genuine build-time-vs-runtime
split in what the app needs."*

This is a stronger, more complete answer than a blanket "multi-stage is
always smaller" — it shows real measurement AND an understanding of
*why* the two halves of the same project behaved so differently.
