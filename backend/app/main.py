from fastapi import FastAPI

from app.routes.auth import router as auth_router
from app.routes.course import router as course_router
from app.routes.subject import router as subject_router
from app.routes.student import router as student_router
from app.routes.instructor import router as instructor_router
from app.routes.exam import router as exam_router
from app.routes.question import router as question_router
from app.routes.choice import router as choice_router
from app.routes.exam_session import router as exam_session_router
from app.routes.student_answer import router as student_answer_router

app = FastAPI(
    title="AI ExamGuard API",
    version="1.0.0",
    description="AI-powered online examination and proctoring system"
)

app.include_router(auth_router)
app.include_router(course_router)
app.include_router(subject_router)
app.include_router(student_router)
app.include_router(instructor_router)
app.include_router(exam_router)
app.include_router(question_router)
app.include_router(choice_router)
app.include_router(exam_session_router)
app.include_router(student_answer_router)



@app.get("/", tags=["Health Check"])
def root():
    return {
        "status": "running",
        "application": "AI ExamGuard API",
        "version": "1.0.0"
    }