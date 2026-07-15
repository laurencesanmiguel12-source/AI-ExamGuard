from fastapi import FastAPI

from app.routes.test import router

app = FastAPI(
    title="AI ExamGuard API",
    version="1.0.0"
)

app.include_router(router)


@app.get("/")
def root():
    return {
        "status": "running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }