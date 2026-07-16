from fastapi import FastAPI
from app.routes.course import router as course_router

from app.routes.auth import router as auth_router

app = FastAPI(
    title="AI ExamGuard API",
    version="1.0.0"
)

app.include_router(auth_router)

app.include_router(course_router)


@app.get("/")
def root():
    return {
        "status": "running"
    }