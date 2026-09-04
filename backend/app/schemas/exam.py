from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# Both of these are PERCENTAGES (0-100), not point totals, and neither was bounded before.
#
# passing_score: exam_session_service compares it against `score / total_points * 100`, so 60
# means "60% of the exam", NOT "60 points". The UI hint used to say the opposite; that was fixed
# in 753a400, but nothing stopped the API accepting an out-of-range value entered under the old
# reading. Unbounded, the failure is silent in the worst direction - a points-style value on an
# exam totalling more than 100 points (e.g. 150) makes the exam unpassable with no error, while a
# negative one passes everybody.
#
# max_risk_score: RiskService.score_violations returns min(100, ...), so anything above 100 means
# "never flag" - again silently, and the exam form has always advertised 0-100 for this field
# without the backend enforcing it. Same defect class as passing_score, bounded here for the same
# reason rather than left as the next one to bite.
PERCENTAGE_FIELD = {"ge": 0, "le": 100}


class ExamBase(BaseModel):
    title: str
    description: str | None = None
    duration_minutes: int
    total_points: int = 0
    passing_score: int = Field(**PERCENTAGE_FIELD)
    max_risk_score: int | None = Field(default=None, **PERCENTAGE_FIELD)
    start_time: datetime
    end_time: datetime
    is_active: bool = False
    subject_id: int
    instructor_id: int


class ExamCreate(ExamBase):
    pass


class ExamUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    duration_minutes: int | None = None
    total_points: int | None = None
    passing_score: int | None = Field(default=None, **PERCENTAGE_FIELD)
    max_risk_score: int | None = Field(default=None, **PERCENTAGE_FIELD)
    start_time: datetime | None = None
    end_time: datetime | None = None
    is_active: bool | None = None
    subject_id: int | None = None
    instructor_id: int | None = None


class ExamResponse(ExamBase):
    id: int

    model_config = ConfigDict(
        from_attributes=True
    )