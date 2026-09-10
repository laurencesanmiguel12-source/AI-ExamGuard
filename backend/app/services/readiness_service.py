"""What still stands between a school and running an exam.

The defense panel asked for two things that turn out to be the same thing. They asked that bulk
import be able to link instructors to what it creates, "or alternatively, it can be left floating
then add a workflow to connect them" - and they asked for the semester hierarchy. Once exams hang
off sections, "connect them" stops meaning instructor-to-subject and starts meaning the whole
chain: a subject somebody teaches, opened as a class this term, with students enrolled in it.

So this is one report rather than a reconciliation screen bolted onto the importer. It walks the
program flow in order and names the first step that is not done. An admin who has just imported a
spreadsheet, and an admin returning at the start of a new term, are asking the same question -
"what is left?" - and it has one answer.

Read-only and school-scoped. It creates nothing and fixes nothing; every item links to the screen
that already owns that fix.
"""
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.academic_year import AcademicYear
from app.models.course import Course
from app.models.enrollment import ACTIVE_ENROLLMENT, Enrollment
from app.models.instructor import Instructor
from app.models.instructor_subject import InstructorSubject
from app.models.section import Section
from app.models.subject import Subject
from app.models.term import Term
from app.models.user import User
from app.schemas.readiness import ReadinessItem, SetupReadiness


class ReadinessService:

    @staticmethod
    def report(school_id: int, db: Session) -> SetupReadiness:
        year = (
            db.query(AcademicYear)
            .filter(AcademicYear.school_id == school_id, AcademicYear.is_current.is_(True))
            .first()
        )
        term = (
            db.query(Term)
            .join(AcademicYear, Term.academic_year_id == AcademicYear.id)
            .filter(AcademicYear.school_id == school_id, Term.status == "ACTIVE")
            .order_by(Term.sequence)
            .first()
        )

        # --- floating instructors and subjects (the panel's literal ask) ----------------------
        assigned_instructor_ids = db.query(InstructorSubject.instructor_id).distinct()
        floating_instructors = [
            ReadinessItem(
                id=i.id,
                label=i.instructor_name or i.employee_number,
                detail=f"Employee {i.employee_number}",
            )
            for i in (
                db.query(Instructor)
                .join(User, Instructor.user_id == User.id)
                .filter(
                    User.school_id == school_id,
                    Instructor.id.notin_(assigned_instructor_ids),
                )
                .order_by(Instructor.id)
                .all()
            )
        ]

        assigned_subject_ids = db.query(InstructorSubject.subject_id).distinct()
        floating_subjects = [
            ReadinessItem(id=s.id, label=f"{s.code} {s.name}".strip(), detail=course_code)
            for s, course_code in (
                db.query(Subject, Course.code)
                .join(Course, Subject.course_id == Course.id)
                .filter(
                    Course.school_id == school_id,
                    Subject.id.notin_(assigned_subject_ids),
                )
                .order_by(Subject.id)
                .all()
            )
        ]

        # --- subjects nobody has opened as a class this term ----------------------------------
        # Only meaningful once a term is running: with no active term there is nothing for a
        # section to belong to, and listing every subject in the school as "not opened" would be
        # noise on top of a step that has not been reached yet.
        unopened_subjects: list[ReadinessItem] = []
        if term is not None:
            sectioned_subject_ids = (
                db.query(Section.subject_id).filter(Section.term_id == term.id).distinct()
            )
            unopened_subjects = [
                ReadinessItem(id=s.id, label=f"{s.code} {s.name}".strip(), detail=course_code)
                for s, course_code in (
                    db.query(Subject, Course.code)
                    .join(Course, Subject.course_id == Course.id)
                    .filter(
                        Course.school_id == school_id,
                        Subject.id.notin_(sectioned_subject_ids),
                    )
                    .order_by(Subject.id)
                    .all()
                )
            ]

        # --- sections with nobody in them (the lockout, listed) -------------------------------
        enrolled_counts = (
            db.query(
                Enrollment.section_id.label("section_id"),
                func.count(Enrollment.id).label("n"),
            )
            .filter(Enrollment.status == ACTIVE_ENROLLMENT)
            .group_by(Enrollment.section_id)
            .subquery()
        )

        section_rows = (
            db.query(Section, Subject.code, enrolled_counts.c.n)
            .join(Subject, Section.subject_id == Subject.id)
            .join(Term, Section.term_id == Term.id)
            .join(AcademicYear, Term.academic_year_id == AcademicYear.id)
            .outerjoin(enrolled_counts, enrolled_counts.c.section_id == Section.id)
            .filter(AcademicYear.school_id == school_id)
            .order_by(Section.id)
            .all()
        )
        if term is not None:
            section_rows = [row for row in section_rows if row[0].term_id == term.id]

        empty_sections = [
            ReadinessItem(
                id=section.id,
                label=f"{subject_code} {section.code}".strip(),
                detail="Nobody enrolled",
            )
            for section, subject_code, n in section_rows
            if not n
        ]
        has_a_live_class = any(n for _, _, n in section_rows)

        # --- the first unmet step, in flow order ----------------------------------------------
        if year is None:
            blocking = "Open a school year on the Academic Calendar. Nothing else can be set up until one exists."
        elif term is None:
            blocking = "No term is running. Activate one on the Academic Calendar so classes have somewhere to sit."
        elif not section_rows:
            blocking = f"No sections in {term.name} yet. Open one per class being taught."
        elif not has_a_live_class:
            blocking = "Every section is empty. Enrol students into a class before setting an exam on it."
        else:
            blocking = None

        return SetupReadiness(
            current_year=year.label if year is not None else None,
            active_term=term.name if term is not None else None,
            instructors_without_subjects=floating_instructors,
            subjects_without_instructor=floating_subjects,
            subjects_without_section=unopened_subjects,
            sections_without_enrollment=empty_sections,
            ready=blocking is None,
            blocking_step=blocking,
        )
