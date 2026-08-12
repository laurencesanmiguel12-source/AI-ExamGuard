from pydantic import BaseModel


class InstructorExamSummary(BaseModel):
    exam_id: int
    title: str
    submitted_count: int
    pass_rate: float
    average_percentage: float
    average_risk_score: float


class InstructorAnalytics(BaseModel):
    exams: list[InstructorExamSummary]
    total_exams: int
    overall_pass_rate: float
    overall_average_risk_score: float


class SchoolInstructorSummary(BaseModel):
    instructor_id: int
    instructor_name: str
    exam_count: int
    avg_pass_rate: float
    avg_risk_score: float


class SchoolAnalytics(BaseModel):
    total_exams: int
    aggregate_pass_rate: float
    aggregate_average_risk_score: float
    total_violations: int
    violation_breakdown: dict[str, int]
    instructors: list[SchoolInstructorSummary]
