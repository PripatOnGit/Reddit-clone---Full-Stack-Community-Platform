# Communities Flow — `POST /communities` and `GET /communities`

Read alongside `app/routers/communities.py`. Builds directly on
`deps_flow.md` (`get_current_user`) — read that first if you haven't.

---

## Line-by-line

```python
router = APIRouter(prefix="/communities", tags=["communities"])
```
Same pattern as `auth.py` — every route below gets `/communities`
prepended automatically. `@router.post("")` (an EMPTY path) means
`POST /communities` exactly — no suffix needed since the prefix already
is the whole path.

### `create_community()`

```python
@router.post("", response_model=CommunityOut, status_code=status.HTTP_201_CREATED)
def create_community(
    payload: CommunityCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
```
`payload: CommunityCreate` — request body validated first, as always.
**The new piece:** `current_user: User = Depends(get_current_user)` —
THIS is what makes the route protected. FastAPI runs `get_current_user`
(see `deps_flow.md`) before this function body executes; a `401`/`403`
there means this function never runs at all. On success, `current_user`
here is the real, logged-in `User` object.

```python
    existing = db.query(Community).filter(Community.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Community name already taken")
```
Same duplicate-check pattern as `signup()` — one query, `409` if taken.
Only one field to check here (just `name`), so no `|` (OR) needed,
unlike signup's username-or-email check.

```python
    community = Community(
        name=payload.name,
        description=payload.description,
        owner_id=current_user.id,
    )
    db.add(community)
    db.commit()
    db.refresh(community)
    return community
```
**The actual payoff of `get_current_user` existing:** `owner_id=current_user.id`.
Without that dependency, this route would have no idea WHO is creating
this community — there'd be nothing to put here. Everything else is the
identical add/commit/refresh/return pattern from `signup()`.

### `list_communities()`

```python
@router.get("", response_model=list[CommunityOut])
def list_communities(db: Session = Depends(get_db)):
    return db.query(Community).order_by(Community.name).all()
```
**No `current_user` parameter at all** — this route is intentionally
public. `response_model=list[CommunityOut]` — the `list[...]` wrapper
tells Pydantic "shape EVERY item in this list through `CommunityOut`,"
not the response once as a whole. `.order_by(Community.name)` —
alphabetical, predictable ordering. `.all()` — unlike `.first()`
elsewhere, returns every matching row (no pagination at this size,
matching what was scoped for `/communities`).

---

## Flow diagrams

### `POST /communities`

```
Client          routers/communities.py       core/deps.py         models/community.py
  │                                                                                    
  │ POST /communities                                                                 
  │ Authorization: Bearer <token>                                                     
  │ {name, description}                                                               
  ├────────────────►                                                                  
  │           1. Depends(get_current_user) runs FIRST                                
  │              ├──────────────────►                                                
  │              │  (verify token, look up user --                                  
  │              │   see deps_flow.md -- fail here = 401/403, STOP)                  
  │              ◄──────────────────┤                                                
  │              current_user = real User object                                     
  │                                                                                    
  │           2. FastAPI validates body against CommunityCreate                      
  │                                                                                    
  │           3. Query: does a Community with this name already exist?               
  │              ├─────────────────────────────────────────────►                    
  │              ◄─────────────────────────────────────────────┤                    
  │              if found -> 409 Conflict, STOP HERE                                 
  │                                                                                    
  │           4. new Community(name, description, owner_id=current_user.id)         
  │              db.add() + db.commit() + db.refresh()                              
  │              ├─────────────────────────────────────────────►                    
  │              ◄─────────────────────────────────────────────┤                    
  │                                                                                    
  │           5. return community -> shaped through CommunityOut                     
  │◄────────────────┤                                                                  
  │ 201 Created                                                                       
  │ {id, name, description, owner_id, created_at}                                    
```

### `GET /communities`

```
Client          routers/communities.py       models/community.py
  │                                                                
  │ GET /communities   (no Authorization header needed at all)   
  ├────────────────►                                              
  │           1. Query ALL communities, ORDER BY name             
  │              ├─────────────────────────────►                 
  │              ◄─────────────────────────────┤                 
  │           2. return list -> each item shaped through          
  │              CommunityOut (list[CommunityOut])                
  │◄────────────────┤                                              
  │ 200 OK                                                        
  │ [{id, name, ...}, {id, name, ...}, ...]                       
```

---

## Where SQLAlchemy is used here

Same narrow scope as `auth.py`: `Depends(get_db)` (get a session),
`db.query(Community).filter(...)` / `.order_by(...)` (read), `db.add()`/
`db.commit()`/`db.refresh()` (write). Everything else — the
`Depends(get_current_user)` auth check, `CommunityCreate`/`CommunityOut`
validation and shaping — is different libraries doing different jobs.

---

## Why `list_communities` has no auth, but `create_community` does

**This is a per-route choice, not an app-wide setting.** Each route
decides for itself by including or omitting `Depends(get_current_user)`
in its own function signature — there's no global "everything requires
login" switch anywhere in this app. `create_community` needs it because
it must know WHO owns the new community; `list_communities` doesn't
change any data and doesn't need to know who's asking, so it stays
public.

**One sentence for the interview:** *"Whether a route requires
authentication is decided per-endpoint by whether it declares
`Depends(get_current_user)` in its signature — there's no global
middleware forcing every route to require login, so public read
endpoints and protected write endpoints can coexist naturally."*
