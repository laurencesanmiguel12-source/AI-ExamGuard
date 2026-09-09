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
    """The fields an exam actually carries in its own right."""

    title: str
    description: str | None = None
    duration_minutes: int
    total_points: int = 0
    passing_score: int = Field(**PERCENTAGE_FIELD)
    max_risk_score: int | None = Field(default=None, **PERCENTAGE_FIELD)
    start_time: datetime
    end_time: datetime
    is_active: bool = False


class ExamCreate(ExamBase):
    """A section is now the only thing an exam is filed under, and it is required.

    subject_id and instructor_id are deliberately NOT accepted. The section already names both,
    and a body that could disagree with it is a body that will: an exam claiming a section of
    CS-101 while filing itself under another subject, or recording an instructor who does not
    teach the class it belongs to. Deriving both means they cannot drift apart at all, where
    validating them only reports the disagreement after the fact.
    """

    section_id: int


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
    # Moving an exam to a different section re-derives its subject and instructor. subject_id and
    # instructor_id are gone from here for the same reason they are gone from create: they are
    # facts about the section now, and a settable copy of a derived fact is a copy that goes
    # stale.
    section_id: int | None = None


class ExamResponse(ExamBase):
    id: int
    section_id: int
    # Still stored and still returned - a great deal of scoping and analytics joins through them -
    # but derived from the section on every write rather than supplied by the client.
    subject_id: int
    instructor_id: int
    # Reached through the section, not stored on the exam - the whole point of the hierarchy.
    term_label: str | None = None

    model_config = ConfigDict(
        from_attributes=True
    )