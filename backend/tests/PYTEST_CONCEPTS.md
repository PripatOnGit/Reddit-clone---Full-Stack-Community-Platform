# pytest — Concept Reference

(Same content as the "pytest" entry in the project-root `CONCEPTS.md`,
kept here too since it's directly about this folder.)

## What it does

A testing framework for Python. Auto-discovers test functions (files
named `test_*.py`, functions named `test_*()`) and runs them, reporting
pass/fail with a clear explanation on failure. No classes or
`self.assertEqual(...)` needed like Python's built-in `unittest` — just
plain functions with plain `assert` statements.

## The recipe used in this project

1. **Naming conventions** pytest auto-discovers: `test_*.py` files,
   `test_*()` functions, and `conftest.py` — a special filename loaded
   automatically before any test runs, no import needed, where shared
   setup lives.
2. **Fixtures** — reusable setup, provided via `@pytest.fixture`. A test
   REQUESTS a fixture just by naming it as a parameter
   (`def test_x(client):`) — the same dependency-injection idea as
   FastAPI's `Depends()`, just pytest's version of it.
3. **Fixtures can depend on other fixtures**, and pytest resolves the
   whole chain automatically — this project's chain: `client` →
   `auth_headers` (signup+login, returns headers) → `community` (in
   `test_posts.py`, creates a community, returns its ID).
4. **`@pytest.fixture(autouse=True)`** — runs for EVERY test
   automatically, without being requested by name (used here for
   building/tearing down the schema once per session, and truncating
   the DB before every single test).
5. **Arrange / Act / Assert** — the shape of a test body: set up the
   situation (often via fixtures), perform the one action being tested,
   assert the outcome.

## Why this matters for this project specifically

The fixture chain is what let every test avoid repeating
signup/login/community-creation boilerplate, and `autouse` fixtures are
what make exact assertions (`owner_id == 1`) safe to write — every test
provably starts from a clean, ID-reset database.

See `testing_flow.md` (project root) for the full line-by-line
walkthrough of every file in this folder.
