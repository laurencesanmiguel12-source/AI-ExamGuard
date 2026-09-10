from pydantic import BaseModel


class ReadinessItem(BaseModel):
    """One loose end, named the way it appears on screen rather than by id."""
    id: int
    label: str
    detail: str | None = None


class SetupReadiness(BaseModel):
    """What still stands between this school and running an exam.

    Ordered the way the program flow runs - year, term, catalogue, sections, class lists - so the
    first unmet item is genuinely the next thing to do, not one of six things to choose between.
    """
    current_year: str | None = None
    active_term: str | None = None

    # The panel's "left floating, then add a workflow to connect them": an instructor imported
    # without subject_codes, and a subject nobody was assigned to.
    instructors_without_subjects: list[ReadinessItem] = []
    subjects_without_instructor: list[ReadinessItem] = []

    # Assignment alone no longer lets anyone set an exam - a section does. A subject taught by
    # somebody but never opened as a class this term is the gap that replaced it.
    subjects_without_section: list[ReadinessItem] = []

    # The lockout, reported one more time in the one place that lists every instance at once.
    sections_without_enrollment: list[ReadinessItem] = []

    # True when at least one class could actually sit an exam today.
    ready: bool = False
    # The first unmet step, in flow order, as a sentence. None when ready.
    blocking_step: str | None = None
