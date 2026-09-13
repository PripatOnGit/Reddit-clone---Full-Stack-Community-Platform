# `get_current_user` — Line-by-Line + Worked Example

`app/core/deps.py` is the file that answers "who is making this
request" for any route that needs to know. This is the first *protected*
piece of the app — nothing before this could reject an anonymous
request.

---

## The whole file

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User

bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )
    try:
        claims = decode_token(credentials.credentials)
    except ValueError:
        raise credentials_error

    user = db.get(User, int(claims["sub"]))
    if user is None:
        raise credentials_error

    return user
```

---

## Line-by-line

**Imports (lines 1-7):** gathering tools from four places -- FastAPI
itself (`Depends`, `HTTPException`, `status`), FastAPI's security
helpers (`HTTPBearer`/`HTTPAuthorizationCredentials` -- know how to read
an `Authorization: Bearer <token>` header without us writing any
header-parsing code), and our own already-built pieces (`decode_token`
from Phase 2, `get_db` from Phase 1, `User` from Phase 1). Nothing here
is new machinery -- this file combines pieces that already exist.

**`bearer_scheme = HTTPBearer()`:** one reusable object whose job is
"find the `Authorization` header, pull the token out of it."

**Function signature:**
```python
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
```
Two things handed in automatically by FastAPI: the extracted header
credentials, and a DB session. **If there's no `Authorization` header at
all, `Depends(bearer_scheme)` fails right here -- this function's body
never runs at all.** (This is why a request with no token at all gets
`403`, not `401` -- see the table below.)

**Prepare the error, don't raise it yet:**
```python
    credentials_error = HTTPException(status_code=401, detail="Could not validate credentials")
```
Built once, reused for every failure path below -- guarantees both
failure cases return the exact same message.

**Verify the token:**
```python
    try:
        claims = decode_token(credentials.credentials)
    except ValueError:
        raise credentials_error
```
`credentials.credentials` (confusingly named: `credentials` the
*variable* holds an object, `.credentials` the *attribute* holds the raw
token *string*). `decode_token` checks the JWT's signature and expiry.
Bad/expired/tampered -> `ValueError` -> our `401`.

**Look up the real user:**
```python
    user = db.get(User, int(claims["sub"]))
    if user is None:
        raise credentials_error
    return user
```
`claims["sub"]` is the user ID, stored as TEXT inside the token (JWTs
only hold text/numbers), so `int(...)` converts it back. `db.get(User, id)`
is SQLAlchemy's fastest lookup -- straight to the primary key. If the
user no longer exists (e.g. deleted after the token was issued),
reject. Otherwise return the real object -- this becomes `current_user`
in any route using `Depends(get_current_user)`.

---

## Worked example, with real values

**Setup:** Priya signs up (`user.id = 1`), logs in. `login()` calls
`create_access_token(1)`, producing a real token:
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwiZXhwIjoxNzg5MzIxMjA5LCJpYXQiOjE3ODkzMTc2MDl9.fLlnFOjYAlxb4F3_tmDAf6HhLvqcJZu48hNnOZXhDPI
```
Her frontend stores this and sends `Authorization: Bearer eyJhbGc...`
on a later request, e.g. `POST /communities`.

### Success path — traced step by step

| Code | What actually happens (real values) |
|---|---|
| `credentials.credentials` | The raw string above, pulled from her request header by `HTTPBearer` |
| `claims = decode_token(...)` | `{'sub': '1', 'exp': 1789321209, 'iat': 1789317609}` — proof this token was signed by us and hasn't expired |
| `int(claims["sub"])` | `'1'` (text) → `1` (real int) |
| `db.get(User, 1)` | Finds the actual row: `priya`, `priya@example.com` |
| `return user` | This `User` object becomes `current_user` inside `create_community` |

### Failure path — traced step by step

A request arrives with `Authorization: Bearer this-is-not-a-real-token-at-all`:
```python
decode_token("this-is-not-a-real-token-at-all")
# -> raises ValueError("Invalid or expired token")
```
`except ValueError: raise credentials_error` fires **immediately** —
`db.get()` is **never even reached**, the database is never queried at
all, and the client gets `401 {"detail": "Could not validate credentials"}`.

### The two different rejection status codes, and why

| Scenario | Status | Who raises it |
|---|---|---|
| No `Authorization` header at all | `403` | `HTTPBearer` itself, before `get_current_user`'s body ever runs |
| Header present, but token is invalid/expired | `401` | Our own code, inside `get_current_user` |
| Header present, token valid, but user no longer exists | `401` | Our own code, `db.get()` returned `None` |

---

## One sentence for the interview

*"`get_current_user` pulls the bearer token out of the request header,
verifies it's a genuine token I signed that hasn't expired, does one
primary-key lookup for the user it belongs to, and returns that real
`User` object — or rejects the request at whichever step fails first,
without ever reaching the database if the token itself is already bad."*
