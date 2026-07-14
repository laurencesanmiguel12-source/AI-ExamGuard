from fastapi import FastAPI

app = FastAPI(
    title="AI ExamGuard API",
    description="Backend API for AI ExamGuard",
    version="1.0.0"
)


@app.get("/")
async def root():
    return {
        "status": "running",
        "application": "AI ExamGuard",
        "version": "1.0.0"
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy"
    }