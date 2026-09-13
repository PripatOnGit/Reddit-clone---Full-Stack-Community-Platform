# Frontend Flow — `api.js` + `App.jsx`

Deliberately unstyled/minimal per explicit request — functional
coverage only. Read alongside `frontend/src/api.js` and
`frontend/src/App.jsx`.

---

## `api.js` — line-by-line

```javascript
const API_BASE = "http://localhost:8000";
```
The backend's address, hardcoded for local dev. (A real deployed app
would read this from a build-time environment variable instead.)

```javascript
async function apiFetch(path, options = {}) {
  const token = localStorage.getItem("access_token");
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
```
THE central function every API call goes through. `localStorage.getItem("access_token")`
reads the JWT back out of browser storage — **this is where the token
actually lives in v3: plain browser `localStorage`, no cookies at all**.
If a token exists, attach it as `Authorization` on EVERY request
automatically — routes that don't check for it (like `GET /communities`)
simply ignore the extra header.

```javascript
  const res = await fetch(API_BASE + path, { ...options, headers });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || res.statusText);
  }
  if (res.status === 204) return null;
  return res.json();
}
```
`res.ok` is `false` for any non-2xx status. On failure, read the error
body (backend always sends `{"detail": "..."}`) and throw a real JS
`Error` with that message — this is what every component's
`catch (err) { setError(err.message) }` displays. Otherwise parse and
return the JSON body.

```javascript
export const api = {
  signup: (data) => apiFetch("/auth/signup", { method: "POST", body: JSON.stringify(data) }),
  login: async (data) => {
    const result = await apiFetch("/auth/login", { method: "POST", body: JSON.stringify(data) });
    localStorage.setItem("access_token", result.access_token);
    return result;
  },
  logout: () => localStorage.removeItem("access_token"),
  isLoggedIn: () => !!localStorage.getItem("access_token"),

  listCommunities: () => apiFetch("/communities"),
  createCommunity: (data) => apiFetch("/communities", { method: "POST", body: JSON.stringify(data) }),

  listPosts: (communityId, page = 1) => apiFetch(`/communities/${communityId}/posts?page=${page}`),
  createPost: (communityId, data) =>
    apiFetch(`/communities/${communityId}/posts`, { method: "POST", body: JSON.stringify(data) }),
};
```
Named wrappers around `apiFetch` for each backend endpoint — nothing
else in the app calls `apiFetch` directly. **`login` is the only
function that writes to `localStorage`** (`setItem`) — the one place a
new token is ever received. `logout` is the mirror — `removeItem` —
and notice **that IS the entire logout implementation**: no API call to
the backend at all, matching `auth_flow.md`'s explanation that there's
no server-side session to revoke. `isLoggedIn()` is a simple boolean
check `App` uses to pick the starting screen.

---

## `App.jsx` — the key pieces

```javascript
export default function App() {
  const [loggedIn, setLoggedIn] = useState(api.isLoggedIn());
  const [community, setCommunity] = useState(null);

  if (!loggedIn) return <AuthForm onAuthed={() => setLoggedIn(true)} />;
```
`useState(api.isLoggedIn())` checks `localStorage` ONCE, when the
component first renders, to decide the starting screen. No token →
show `AuthForm`, nothing else renders until `onAuthed()` flips
`loggedIn` to `true`.

```javascript
{!community && <CommunitiesView onSelect={setCommunity} />}
{community && <PostsView community={community} onBack={() => setCommunity(null)} />}
```
Same view-switching pattern as the backend's route structure implies —
`community` being `null` or a real object decides which screen shows.
No router library — just plain React state.

### The pagination piece, in `PostsView`

```javascript
const [data, setData] = useState({ items: [], total: 0, page: 1, page_size: 20 });
...
const totalPages = Math.ceil(data.total / data.page_size) || 1;
...
<button disabled={data.page <= 1} onClick={() => load(data.page - 1)}>Prev</button>
<button disabled={data.page >= totalPages} onClick={() => load(data.page + 1)}>Next</button>
```
`data` holds the ENTIRE `PaginatedPosts` response shape from the
backend (`items`, `total`, `page`, `page_size`) — matches the schema
exactly. `totalPages` is computed CLIENT-SIDE from `total`/`page_size`
— this is exactly why the backend bothers sending `total` at all, not
just the page's items. `Prev`/`Next` call `load(page ± 1)` and
auto-disable at the boundaries using that same computed `totalPages`.

---

## Why CORS had to be added to the backend for this to work

Frontend (`:5173`) and backend (`:8000`) are different origins (same
host, different port still counts as a different origin to the
browser). Without `CORSMiddleware` on the backend, the browser blocks
the frontend's `fetch()` calls from reading the response at all —
regardless of whether cookies are involved. **v3's CORS setup is
simpler than v2's** — no `allow_credentials=True` needed, because there
are no cookies to send cross-origin; the token travels in a header the
frontend attaches itself, not something the browser manages
automatically.

---

## Verified behavior (real browser test)

Full flow run via a real headless browser (Playwright) against both
live servers: signup → login → create community → create post →
pagination UI (`Page 1 of 1 (1 posts total)`, `Prev`/`Next` correctly
disabled at 1 page) → logout, with **zero console errors** — cleaner
than v2's equivalent test, which had two expected 401s from an
unauthenticated startup check v3 doesn't have (no `/auth/me`-style
"am I logged in" probe on load).

**One sentence for the interview:** *"The frontend stores the JWT in
`localStorage` and attaches it as an `Authorization` header on every
request through one central `apiFetch` function — logout is just
deleting that token client-side, with zero backend involvement, which
directly reflects the backend having no server-side session to revoke."*
