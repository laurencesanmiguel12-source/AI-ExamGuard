from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.auth import router as auth_router
from app.routes.course import router as course_router
from app.routes.subject import router as subject_router
from app.routes.student import router as student_router
from app.routes.instructor import router as instructor_router
from app.routes.exam import router as exam_router
from app.routes.question import router as question_router
from app.routes.choice import router as choice_router
from app.routes.violation import router as violation_router
from app.routes.exam_session import router as exam_session_router
from app.routes.student_answer import router as student_answer_router
from app.routes.report import router as report_router
from app.routes.face import router as face_router
from app.routes.object_detection import router as object_detection_router

app = FastAPI(
    title="AI ExamGuard API",
    version="1.0.0",
    description="AI-powered online examination and proctoring system"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(course_router)
app.include_router(subject_router)
app.include_router(student_router)
app.include_router(instructor_router)
app.include_router(exam_router)
app.include_router(question_router)
app.include_router(choice_router)
app.include_router(violation_router)
app.include_router(exam_session_router)
app.include_router(student_answer_router)
app.include_router(report_router)
app.include_router(face_router)
app.include_router(object_detection_router)



@app.get("/", tags=["Health Check"])
def root():
    return {
        "status": "running",
        "application": "AI ExamGuard API",
        "version": "1.0.0"
    }