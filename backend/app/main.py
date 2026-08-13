from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.config import settings
from app.core.rate_limit import limiter
from app.routes.auth import router as auth_router
from app.routes.school import router as school_router
from app.routes.course import router as course_router
from app.routes.subject import router as subject_router
from app.routes.student import router as student_router
from app.routes.instructor import router as instructor_router
from app.routes.instructor_subject import router as instructor_subject_router
from app.routes.exam import router as exam_router
from app.routes.exam_content import router as exam_content_router
from app.routes.exam_roster import router as exam_roster_router
from app.routes.violation import router as violation_router
from app.routes.violation import violations_router
from app.routes.exam_session import router as exam_session_router
from app.routes.student_answer import router as student_answer_router
from app.routes.report import router as report_router
from app.routes.analytics import router as analytics_router
from app.routes.face import router as face_router
from app.routes.object_detection import router as object_detection_router
from app.routes.system import router as system_router
from app.routes.audit_log import router as audit_log_router
from app.routes.retention import router as retention_router
from app.routes.training_review import router as training_review_router

app = FastAPI(
    title="AI ExamGuard API",
    version="1.0.0",
    description="AI-powered online examination and proctoring system"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.include_router(auth_router)
app.include_router(school_router)
app.include_router(course_router)
app.include_router(subject_router)
app.include_router(student_router)
app.include_router(instructor_router)
app.include_router(instructor_subject_router)
app.include_router(exam_router)
app.include_router(exam_content_router)
app.include_router(exam_roster_router)
app.include_router(violation_router)
app.include_router(violations_router)
app.include_router(exam_session_router)
app.include_router(student_answer_router)
app.include_router(report_router)
app.include_router(analytics_router)
app.include_router(face_router)
app.include_router(object_detection_router)
app.include_router(system_router)
app.include_router(audit_log_router)
app.include_router(retention_router)
app.include_router(training_review_router)



@app.get("/", tags=["Health Check"])
def root():
    return {
        "status": "running",
        "application": "AI ExamGuard API",
        "version": "1.0.0"
    }