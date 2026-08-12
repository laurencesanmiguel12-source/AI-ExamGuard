from datetime import datetime

from pydantic import BaseModel


class AttemptReport(BaseModel):
    session_id: int
    student_id: int
    student_number: str
    student_name: str
    started_at: datetime
    submitted_at: datetime | None
    status: str
    score: int
    percentage: float
    passed: bool


class QuestionReport(BaseModel):
    question_id: int
    question_text: str
    question_type: str
    points: int
    answered_count: int
    correct_count: int
    accuracy: float


class ExamReport(BaseModel):
    exam_id: int
    title: str
    total_points: int
    passing_score: int
    total_attempts: int
    submitted_count: int
    in_progress_count: int
    average_score: float
    average_percentage: float
    pass_count: int
    fail_count: int
    pass_rate: float
    attempts: list[AttemptReport]
    questions: list[QuestionReport]
    violation_breakdown: dict[str, int]
    average_risk_score: float
    risk_distribution: dict[str, int]
