from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, communities, posts

app = FastAPI(title="Reddit Clone API (v3)")

# frontend (:5173) and backend (:8000) are different origins -- the browser
# blocks cross-origin fetch() reads without this, even for header-based auth
# (no cookies involved, so allow_credentials isn't needed here, unlike v2)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(communities.router)
app.include_router(posts.router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
