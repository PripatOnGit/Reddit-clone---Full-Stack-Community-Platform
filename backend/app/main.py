from fastapi import FastAPI

from app.routers import auth, communities, posts

app = FastAPI(title="Reddit Clone API (v3)")

app.include_router(auth.router)
app.include_router(communities.router)
app.include_router(posts.router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
