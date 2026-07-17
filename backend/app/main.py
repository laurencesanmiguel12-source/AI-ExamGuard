from fastapi import FastAPI

from app.routes.auth import router as auth_router
from app.routes.course import router as course_router
from app.routes.subject import router as subject_router

app = FastAPI(
    title="AI ExamGuard API",
    version="1.0.0",
    description="AI-powered online examination and proctoring system"
)

app.include_router(auth_router)
app.include_router(course_router)
app.include_router(subject_router)


@app.get("/", tags=["Health Check"])
def root():
    return {
        "status": "running",
        "application": "AI ExamGuard API",
        "version": "1.0.0"
    }