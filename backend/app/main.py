from fastapi import FastAPI

app = FastAPI(title="Reddit Clone API (v3)")


@app.get("/health")
def health_check():
    return {"status": "ok"}
