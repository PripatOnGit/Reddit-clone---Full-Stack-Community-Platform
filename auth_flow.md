# Auth Flow — `POST /auth/signup` and `POST /auth/login`

One diagram + code walkthrough per endpoint. Read this alongside
`app/routers/auth.py`.

---

## `POST /auth/signup`

### Flow diagram

```
Client                main.py         routers/auth.py         schemas/user.py      db/session.py      models/user.py      core/security.py
  │                                                                                                                              
  │ POST /auth/signup                                                                                                           
  │ {username, email, password}                                                                                                 
  ├──────────────────────►                                                                                                      
  │                 include_router()                                                                                            
  │                 routes to auth.py                                                                                           
  │                       ├───────────────────►                                                                                 
  │                       │            1. FastAPI validates body                                                                
  │                       │               against UserCreate                                                                   
  │                       │               ├───────────────────►                                                                
  │                       │               │  (missing/wrong-type field                                                        
  │                       │               │   -> 422, function never runs)                                                    
  │                       │                                                                                                     
  │                       │            2. get_db() hands in a                                                                  
  │                       │               fresh DB session                                                                    
  │                       │               ├─────────────────────────────────►                                                 
  │                       │                                                                                                     
  │                       │            3. Query: does a User already                                                          
  │                       │               exist with this username OR email?                                                  
  │                       │               ├──────────────────────────────────────────────────►                               
  │                       │               ◄──────────────────────────────────────────────────┤                               
  │                       │               if found -> 409 Conflict, STOP HERE                                                 
  │                       │                                                                                                     
  │                       │            4. hash_password(payload.password)                                                     
  │                       │               ├────────────────────────────────────────────────────────────────────────────────► 
  │                       │               ◄────────────────────────────────────────────────────────────────────────────────┤ 
  │                       │               (bcrypt hash, e.g. "$2b$12$...")                                                    
  │                       │                                                                                                     
  │                       │            5. new User(username, email, password_hash)                                            
  │                       │               db.add() + db.commit() + db.refresh()                                               
  │                       │               ├──────────────────────────────────────────────────►                               
  │                       │               ◄──────────────────────────────────────────────────┤                               
  │                       │               (row saved, id + created_at now populated)                                          
  │                       │                                                                                                     
  │                       │            6. return user -> shaped through UserOut                                               
  │                       │               (id, username, email, created_at --                                                 
  │                       │                password_hash NEVER included)                                                      
  │                       │               ├───────────────────►                                                                
  │◄──────────────────────┤                                                                                                     
  │ 201 Created                                                                                                                
  │ {id, username, email, created_at}                                                                                          
```

### Code, annotated

```python
@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def signup(payload: UserCreate, db: Session = Depends(get_db)):
    # Step 3: one query checks BOTH username and email at once (SQL OR)
    existing = db.query(User).filter(
        (User.username == payload.username) | (User.email == payload.email)
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username or email already registered")

    # Step 4 + 5: hash the password, build the row, save it
    user = User(
        username=payload.username,
        email=payload.email,
        password_hash=hash_password(payload.password),  # raw password never stored
    )
    db.add(user)      # stage it
    db.commit()        # actually write to Postgres -- point of no return
    db.refresh(user)     # re-read id/created_at, which the DB generated

    # Step 6: return value passes through UserOut (response_model) automatically
    return user
```

**Key point:** the raw `payload.password` is read exactly once, fed straight
into `hash_password()`, and the original value is never assigned to
anything else, never logged, never stored. `user.password_hash` is the
only thing that ever touches the database.

---

## `POST /auth/login`

### Flow diagram

```
Client              routers/auth.py       models/user.py      core/security.py
  │                                                                              
  │ POST /auth/login                                                            
  │ {username, password}                                                        
  ├──────────────────►                                                          
  │            1. FastAPI validates body                                        
  │               against LoginRequest                                         
  │                                                                              
  │            2. Query User by username                                       
  │               ├──────────────────────────────►                             
  │               ◄──────────────────────────────┤                             
  │               (found, or None)                                             
  │                                                                              
  │            3. if not user OR not verify_password(...):                     
  │                                    ├────────────────────────►              
  │                                    ◄────────────────────────┤              
  │                                    (re-hash attempt, compare)               
  │               -> 401 Unauthorized (SAME message either way), STOP HERE     
  │                                                                              
  │            4. create_access_token(user.id)                                 
  │                                    ├────────────────────────►              
  │                                    ◄────────────────────────┤              
  │                                    (signed JWT string)                     
  │                                                                              
  │            5. return TokenResponse(access_token=...)                       
  │◄──────────────────┤                                                        
  │ 200 OK                                                                      
  │ {access_token, token_type: "bearer"}                                       
```

### Code, annotated

```python
@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    # Step 2
    user = db.query(User).filter(User.username == payload.username).first()

    # Step 3: `not user` short-circuits -- if there's no user at all,
    # verify_password() is never called (would crash on user.password_hash
    # if user were None). SAME error message for "no such user" and "wrong
    # password" -- doesn't reveal to an attacker which usernames exist.
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")

    # Step 4 + 5
    access_token = create_access_token(user.id)
    return TokenResponse(access_token=access_token)
```

---

## Where SQLAlchemy actually gets used in this flow

Easy to lose track of which parts are SQLAlchemy vs. Pydantic vs. plain
FastAPI once it's all in one function. Marked explicitly:

```python
def signup(payload: UserCreate, db: Session = Depends(get_db)):
    #                            ^^^^^^^ SQLAlchemy -- `Session` is a SQLAlchemy
    #                            type; `get_db()` (db/session.py) hands in an
    #                            actual SQLAlchemy session for this request

    existing = db.query(User).filter(...).first()
    #          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ SQLAlchemy -- builds and runs
    #          a real SELECT against Postgres, returns a User object or None

    user = User(username=..., email=..., password_hash=...)
    #      ^^^^ SQLAlchemy -- constructing an instance of a mapped model class
    #      (NOT saved to the DB yet -- just an in-memory Python object so far)

    db.add(user)       # SQLAlchemy -- stage this object to be inserted
    db.commit()         # SQLAlchemy -- actually send the INSERT to Postgres
    db.refresh(user)      # SQLAlchemy -- re-read the row back (picks up id/created_at)

    return user   # <- NOT SQLAlchemy from here: `response_model=UserOut` (Pydantic)
                  #    takes over, reading attributes off this SQLAlchemy object
                  #    and building the JSON response from them
```

```python
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    #      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ SQLAlchemy again
    #      -- same pattern: build + run a SELECT, get back an object or None

    if not user or not verify_password(...):   # verify_password is core/security.py -- NOT SQLAlchemy at all
        raise HTTPException(...)

    access_token = create_access_token(user.id)   # NOT SQLAlchemy -- `user.id` is just
                                                     # reading a plain Python attribute off
                                                     # the object SQLAlchemy already gave us
```

**The pattern to notice:** SQLAlchemy's involvement is narrowly scoped to
exactly three things in this whole file — (1) `Depends(get_db)` getting a
session, (2) `db.query(...)` reading data, (3) `db.add()`/`db.commit()`/
`db.refresh()` writing data. Everything else — validating the request
(`UserCreate`/`LoginRequest`), hashing passwords, building the JWT,
shaping the response (`UserOut`/`TokenResponse`) — is a **different**
library doing a **different** job. SQLAlchemy's entire role in this file
is "get data in and out of Postgres" — nothing more, nothing less.

---

## Why there's no `POST /auth/logout`

v3 has exactly one JWT, no rotation, no server-side session table. There
is nothing on the server to revoke. "Logging out" is a **frontend-only**
action: delete the stored token from `localStorage`. The token itself
remains technically valid (would still pass `decode_token()`) until its
own expiry — it's just no longer sitting in the browser to be sent.
