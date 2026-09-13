# Posts Flow — `POST` and `GET /communities/{id}/posts`

Read alongside `app/schemas/post.py` and `app/routers/posts.py`. Builds
on `deps_flow.md` and `communities_flow.md`.

---

## `app/schemas/post.py` — line-by-line

```python
class PostCreate(BaseModel):
    title: str
    content: str | None = None
```
What a client sends to create a post. `title` required, `content`
optional (`str | None = None` — a title-only post is valid).

```python
class PostOut(BaseModel):
    id: int
    title: str
    content: str | None
    author_id: int
    community_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
```
What a post looks like in a response. Includes `author_id`/`community_id`
even though neither comes from the client's own request body — both get
set server-side (see the router below). `from_attributes=True` lets this
schema read straight off a SQLAlchemy `Post` object's attributes.

```python
class PaginatedPosts(BaseModel):
    items: list[PostOut]
    total: int
    page: int
    page_size: int
```
The pagination wrapper. `items` = this page's posts. `total` = how many
posts exist ACROSS ALL pages (lets a frontend compute
`total_pages = ceil(total / page_size)`). `page`/`page_size` echo back
what was requested. **Why wrap instead of returning a bare
`list[PostOut]`** (like `communities` does): a bare list alone can't
tell the client whether there's more data beyond what's shown.

---

## `app/routers/posts.py` — line-by-line

```python
router = APIRouter(tags=["posts"])
```
**No `prefix=`** here, unlike `auth.py`/`communities.py` — because these
routes nest under `/communities/{id}/...` rather than one flat prefix,
the full path is written out in each `@router` decorator instead.

```python
def _get_community_or_404(db: Session, community_id: int) -> Community:
    community = db.get(Community, community_id)
    if community is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Community not found")
    return community
```
A shared helper, used by BOTH endpoints below — same DRY reasoning as
`get_current_user` living in its own file: written once instead of
repeated in every route that needs "does this community exist."

### `create_post()`

```python
@router.post("/communities/{community_id}/posts", response_model=PostOut, status_code=status.HTTP_201_CREATED)
def create_post(
    community_id: int,
    payload: PostCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
```
`{community_id}` in the path + `community_id: int` as a parameter —
FastAPI extracts the URL segment, converts it to `int` automatically.

```python
    _get_community_or_404(db, community_id)

    post = Post(
        title=payload.title,
        content=payload.content,
        author_id=current_user.id,
        community_id=community_id,
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return post
```
Check the community exists first (clear `404` if not). Then create —
**`author_id` and `community_id` both come from OUTSIDE the request
body**: `author_id` from `get_current_user` (who's logged in),
`community_id` from the URL path. Neither is client-controlled via
JSON — deliberate, so a client can't claim to post as someone else or
into an arbitrary community by editing a field.

### `list_posts()` — the pagination math

```python
@router.get("/communities/{community_id}/posts", response_model=PaginatedPosts)
def list_posts(
    community_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
```
`page`/`page_size` come from QUERY STRING params (`?page=2&page_size=10`),
not the path. `Query(default=1, ge=1)` — defaults to page 1;
`ge=1` auto-rejects `?page=0` or negative values with `422`, before the
function runs at all. `page_size` capped `le=100` — stops a client
requesting an absurd page size in one shot.

```python
    _get_community_or_404(db, community_id)

    base_query = db.query(Post).filter(Post.community_id == community_id)
    total = base_query.count()
```
Build the filter once, reuse it for both the count and the page fetch
below (not duplicated). `.count()` is a SEPARATE query asking Postgres
"how many rows match this, total" — this is where `total` comes from.

```python
    items = (
        base_query.order_by(Post.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
```
**The actual pagination formula: `offset = (page - 1) * page_size`.**
Page 1 → offset 0 (skip nothing). Page 2 → offset 20 (skip the first
20). Page 3 → offset 40. `.order_by(created_at.desc())` — newest first,
giving pagination a CONSISTENT order (without an explicit order, which
rows land on which page isn't even guaranteed stable across calls).

```python
    return PaginatedPosts(items=items, total=total, page=page, page_size=page_size)
```
Package it all into the schema — client gets this page's posts plus
enough context to know if there's more.

---

## Flow diagrams

### `POST /communities/{community_id}/posts`

```
Client              routers/posts.py         core/deps.py      models/community.py   models/post.py
  │                                                                                                   
  │ POST /communities/1/posts                                                                        
  │ Authorization: Bearer <token>                                                                     
  │ {title, content}                                                                                   
  ├────────────────►                                                                                  
  │           1. Depends(get_current_user) runs FIRST                                                
  │              ├──────────────►                                                                     
  │              ◄──────────────┤  current_user = real User (fail = 401/403, STOP)                   
  │                                                                                                    
  │           2. FastAPI validates body against PostCreate                                            
  │                                                                                                    
  │           3. _get_community_or_404(db, 1)                                                          
  │              ├────────────────────────────────────►                                               
  │              ◄────────────────────────────────────┤  (not found -> 404, STOP)                     
  │                                                                                                    
  │           4. new Post(title, content,                                                              
  │              author_id=current_user.id, community_id=1)                                           
  │              db.add() + commit() + refresh()                                                      
  │              ├──────────────────────────────────────────────────────────►                        
  │              ◄──────────────────────────────────────────────────────────┤                        
  │                                                                                                    
  │           5. return post -> shaped through PostOut                                                
  │◄────────────────┤                                                                                  
  │ 201 Created                                                                                        
  │ {id, title, content, author_id, community_id, created_at}                                          
```

### `GET /communities/{community_id}/posts?page=2&page_size=20`

```
Client              routers/posts.py         models/community.py   models/post.py
  │                                                                                
  │ GET /communities/1/posts?page=2&page_size=20                                 
  ├────────────────►                                                              
  │           1. page/page_size validated (Query ge=1/le=100) -- bad value = 422 
  │                                                                                
  │           2. _get_community_or_404(db, 1)                                    
  │              ├────────────────────────────────────►                          
  │              ◄────────────────────────────────────┤  (not found -> 404, STOP)
  │                                                                                
  │           3. total = base_query.count()                                      
  │              ├──────────────────────────────────────────────────►           
  │              ◄──────────────────────────────────────────────────┤           
  │                                                                                
  │           4. items = base_query.order_by(created_at.desc())                  
  │              .offset((2-1)*20).limit(20).all()                               
  │              ├──────────────────────────────────────────────────►           
  │              ◄──────────────────────────────────────────────────┤           
  │                                                                                
  │           5. return PaginatedPosts(items, total, page, page_size)            
  │◄────────────────┤                                                              
  │ 200 OK                                                                        
  │ {items: [...20 posts...], total: 25, page: 2, page_size: 20}                 
```

---

## Where SQLAlchemy is used

Same narrow scope as before: `Depends(get_db)`, `db.get()`/`db.query()`/
`.filter()`/`.count()`/`.order_by()`/`.offset()`/`.limit()`/`.all()`
(reading), `db.add()`/`.commit()`/`.refresh()` (writing). Pagination
itself (`.offset()`/`.limit()`) is just two more SQLAlchemy query
methods — no separate pagination library needed.

---

## Verified behavior (real test run)

25 posts created in one community → page 1 (`page_size=20` default)
returned exactly 20 items with `total: 25`; page 2 returned exactly the
remaining 5; `?page=0` rejected with `422` before the route ran;
requesting posts for a nonexistent community `404`s on both create and
list.

**One sentence for the interview:** *"Pagination is `offset = (page-1) * page_size` with an explicit `ORDER BY` for a stable sequence, plus a separate `COUNT` query so the client knows the total — both are just SQLAlchemy query methods, no separate library needed."*
