# Testing Flow — Line-by-Line for Every Test File

Read alongside `backend/tests/`. Four files: `conftest.py` (shared
setup, no tests of its own), `test_auth.py`, `test_communities.py`,
`test_posts.py`.

---

## `tests/conftest.py` — line-by-line

```python
from app.core.config import settings
...
TEST_DATABASE_URL = settings.database_url.rsplit("/", 1)[0] + "/reddit_clone_v3_test"
```
Builds a SEPARATE database URL — same server, same credentials, but a
different database name (`reddit_clone_v3_test` instead of
`reddit_clone_v3`). `.rsplit("/", 1)[0]` splits the URL at the LAST `/`
and keeps everything before it (i.e. everything except the original
database name), then appends the test database name. This is why tests
can never accidentally touch real dev data — they're physically talking
to a different database.

```python
engine = create_engine(TEST_DATABASE_URL)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
```
The SAME pattern as `db/session.py`'s real `engine`/`SessionLocal` —
just pointed at the test database instead.

```python
_TABLES_IN_DELETE_ORDER = ["posts", "communities", "users"]
```
Child tables before parent tables — `posts` references `communities`
and `users`, `communities` references `users`. Listed in this order so
`TRUNCATE` (below) doesn't fight foreign key constraints. (In practice
`TRUNCATE ... CASCADE` handles the ordering automatically, but listing
tables in a foreign-key-aware order is still the clearer habit.)

```python
@pytest.fixture(scope="session", autouse=True)
def _create_schema():
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)
```
Runs ONCE for the entire test session (`scope="session"`), automatically
(`autouse=True` — no test has to explicitly ask for this fixture, it
just always runs). Builds every table before ANY test runs, and drops
them all after the LAST test finishes. The `yield` is the same
pause-and-resume mechanic from `get_db()` — code before `yield` runs at
setup, code after runs at teardown.

```python
@pytest.fixture(autouse=True)
def _clean_database():
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {', '.join(_TABLES_IN_DELETE_ORDER)} RESTART IDENTITY CASCADE"))
    yield
```
Runs before EVERY SINGLE test (no `scope=`, so it defaults to
per-test), also automatic. Wipes all rows and resets auto-increment IDs
back to 1 — this is WHY `test_create_community_success` can safely
assert `owner_id == 1`: every test starts from a guaranteed-empty,
guaranteed-ID-reset database.

```python
def _override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = _override_get_db
```
An exact copy of the real `get_db()`'s shape, just using `TestSessionLocal`
instead. `app.dependency_overrides[get_db] = _override_get_db` is
FastAPI's built-in mechanism: "wherever any route says
`Depends(get_db)`, use THIS function instead, for the whole app." Zero
route code changes needed — `communities.py`/`posts.py` are completely
unaware they're now talking to a test database.

```python
@pytest.fixture
def client():
    return TestClient(app)
```
Not `autouse` — tests that need it ask for it explicitly (as a function
parameter named `client`, matching this fixture's name — that's how
pytest connects a test to a fixture).

```python
@pytest.fixture
def auth_headers(client):
    client.post("/auth/signup", json={"username": "alice", "email": "alice@example.com", "password": "testpass123"})
    r = client.post("/auth/login", json={"username": "alice", "password": "testpass123"})
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
```
A fixture that DEPENDS ON ANOTHER FIXTURE (`client` as its own
parameter) — pytest resolves this chain automatically. Does the
signup+login dance once, hands back ready-to-use headers. Any test
needing "a logged-in user" just adds `auth_headers` as a parameter,
without repeating this boilerplate.

---

## `tests/test_auth.py` — line-by-line

```python
def test_signup_creates_user_without_password_fields(client):
    r = client.post("/auth/signup", json={"username": "bob", "email": "bob@example.com", "password": "testpass123"})
    assert r.status_code == 201
    body = r.json()
    assert body["username"] == "bob"
    assert "password" not in body
    assert "password_hash" not in body
```
`client` here is the fixture from `conftest.py`, requested by parameter
name. Confirms both the HTTP status AND — critically — that the
response body structurally cannot contain password data, proving
`UserOut`'s field-exclusion actually works, not just in theory.

```python
def test_signup_duplicate_username_rejected(client):
    client.post("/auth/signup", json={"username": "bob", ...})
    r = client.post("/auth/signup", json={"username": "bob", ...})
    assert r.status_code == 409
```
Signs up the SAME username twice in one test — the second call is the
one actually being tested.

```python
def test_login_nonexistent_user_same_error_as_wrong_password(client):
    r = client.post("/auth/login", json={"username": "ghost", "password": "whatever"})
    assert r.status_code == 401
    assert r.json()["detail"] == "Incorrect username or password"
```
Directly tests the "same error message either way" design decision from
`auth_flow.md`'s Q2 — no signup happens first, `"ghost"` never existed
at all, and the exact wording is asserted, not just the status code.

```python
def test_login_returns_usable_token(client):
    ...
    assert "access_token" in r.json()
    assert r.json()["token_type"] == "bearer"
```
Checks the SHAPE of a successful login response, not just that it
succeeded.

---

## `tests/test_communities.py` — line-by-line

```python
def test_create_community_requires_auth(client):
    r = client.post("/communities", json={"name": "python"})
    assert r.status_code == 403  # HTTPBearer itself rejects -- no header at all
```
No `Authorization` header sent at all — tests the `403` case
specifically (`HTTPBearer` rejecting before `get_current_user` even
runs, per `deps_flow.md`'s status-code table).

```python
def test_create_community_with_bad_token_rejected(client):
    r = client.post("/communities", json={"name": "python"}, headers={"Authorization": "Bearer garbage"})
    assert r.status_code == 401  # our own check inside get_current_user
```
A header IS present, but the token itself is garbage — tests the OTHER
half of that same status-code table: our own `401`, not `HTTPBearer`'s
`403`. Together, these two tests prove both rejection paths actually
behave as documented.

```python
def test_create_community_success(client, auth_headers):
    r = client.post("/communities", json={"name": "python", "description": "py talk"}, headers=auth_headers)
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "python"
    assert body["owner_id"] == 1
```
`auth_headers` requested as a parameter — pytest automatically runs
that fixture (which itself runs `client`) before this test body starts.
`owner_id == 1` is only a safe, exact assertion because of
`_clean_database`'s `RESTART IDENTITY` — the very first user created in
this test gets ID 1, guaranteed.

```python
def test_list_communities_requires_no_auth(client, auth_headers):
    client.post("/communities", json={"name": "python"}, headers=auth_headers)
    r = client.get("/communities")  # no headers at all
    assert r.status_code == 200
```
Creates a community WITH auth, then reads the list WITHOUT any — proves
`list_communities` is genuinely public, not just "happens to not check."

---

## `tests/test_posts.py` — line-by-line

```python
@pytest.fixture
def community(client, auth_headers):
    r = client.post("/communities", json={"name": "python"}, headers=auth_headers)
    return r.json()["id"]
```
A THIRD fixture, local to this file, depending on both `client` and
`auth_headers` — creates a real community and returns just its ID, so
every post-related test can build on top of it without repeating this
setup.

```python
def test_pagination_across_two_pages(client, auth_headers, community):
    for i in range(25):
        client.post(f"/communities/{community}/posts", json={"title": f"post {i}"}, headers=auth_headers)

    r = client.get(f"/communities/{community}/posts", params={"page": 1})
    data = r.json()
    assert data["total"] == 25
    assert len(data["items"]) == 20
    assert data["page"] == 1

    r = client.get(f"/communities/{community}/posts", params={"page": 2})
    data = r.json()
    assert len(data["items"]) == 5
```
This is the test that actually PROVES the pagination formula from
`posts_flow.md` works, not just at page 1 — creates exactly 25 posts,
checks page 1 has exactly 20 with `total: 25` reported correctly, then
checks page 2 has exactly the remaining 5. If the `offset`/`limit` math
were off by one anywhere, this test would catch it immediately.

```python
def test_invalid_page_rejected(client, community):
    r = client.get(f"/communities/{community}/posts", params={"page": 0})
    assert r.status_code == 422

def test_page_size_over_max_rejected(client, community):
    r = client.get(f"/communities/{community}/posts", params={"page_size": 9999})
    assert r.status_code == 422
```
Both test the `Query(ge=1)`/`Query(le=100)` constraints from
`posts_flow.md` — proving FastAPI actually rejects bad values before
`list_posts`'s body ever runs, not just that the constraint LOOKS
correct in the code.

---

## The pattern across all four files, summarized

**Fixtures build on each other** (`client` → `auth_headers` →
`community`), each one handling exactly one piece of setup, reusable by
name. **Every test proves ONE specific behavior** — a status code, a
response shape, or (for pagination) an exact numeric outcome — rather
than vague "does it work" checks. **The database is provably clean
before every test** (`_clean_database`), which is what makes exact
assertions like `owner_id == 1` safe to write at all.
