from fastapi import FastAPI

from app.routers import auth

app = FastAPI(title="Reddit Clone API (v3)")

app.include_router(auth.router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
