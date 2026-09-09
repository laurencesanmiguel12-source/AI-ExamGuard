"""Academic hierarchy: academic years, terms, sections and enrolment.

One service rather than four, because the invariants cross entities - "exactly one current year
per school", "a closed term accepts nothing new", "a section's subject and its instructor must
belong to the same school as its term" - and splitting them up would mean each rule living
somewhere it can be forgotten.

Everything here is school-scoped. `school_id` is always taken from the acting user's session,
never from the request body, for the same reason the bulk-import service does it: a school id
that arrives in a payload is an invitation to write into somebody else's school.
"""
from datetime import date

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.academic_year import AcademicYear
from app.models.enrollment import ACTIVE_ENROLLMENT, ENROLLMENT_STATUSES, Enrollment
from app.models.instructor import Instructor
from app.models.section import Section
from app.models.student import Student
from app.models.subject import Subject
from app.models.course import Course
from app.models.term import TERM_STATUSES, TERM_TRANSITIONS, Term
from app.models.user import User


def _not_found(what: str):
    return HTTPException(status_code=404, detail=f"{what} not found.")


class AcademicService:

    # --- academic years -------------------------------------------------------------------------

    @staticmethod
    def list_years(school_id: int, db: Session) -> list[AcademicYear]:
        return (
            db.query(AcademicYear)
            .filter(AcademicYear.school_id == school_id)
            .order_by(AcademicYear.starts_on.desc())
            .all()
        )

    @staticmethod
    def current_year(school_id: int, db: Session) -> AcademicYear | None:
        return (
            db.query(AcademicYear)
            .filter(AcademicYear.school_id == school_id, AcademicYear.is_current.is_(True))
            .first()
        )

    @staticmethod
    def create_year(label: str, starts_on: date, ends_on: date, make_current: bool,
                    school_id: int, db: Session) -> AcademicYear:
        if ends_on <= starts_on:
            raise HTTPException(status_code=400, detail="An academic year must end after it starts.")

        existing = (
            db.query(AcademicYear)
            .filter(AcademicYear.school_id == school_id, AcademicYear.label == label)
            .first()
        )
        if existing is not None:
            raise HTTPException(status_code=400, detail=f"'{label}' already exists for this school.")

        year = AcademicYear(
            school_id=school_id, label=label,
            starts_on=starts_on, ends_on=ends_on, is_current=False,
        )
        db.add(year)
        db.flush()

        # The very first year is current whether or not anyone asked: a school with years defined
        # but none marked current would make every "current term" view silently empty.
        if make_current or AcademicService.current_year(school_id, db) is None:
            AcademicService.set_current_year(year.id, school_id, db, commit=False)

        db.commit()
        db.refresh(year)
        return year

    @staticmethod
    def set_current_year(year_id: int, school_id: int, db: Session, commit: bool = True) -> AcademicYear:
        """Exactly one current year per school - enforced by clearing the others in the same
        transaction rather than by a partial index, so the invariant holds identically on every
        database this runs against."""
        year = (
            db.query(AcademicYear)
            .filter(AcademicYear.id == year_id, AcademicYear.school_id == school_id)
            .first()
        )
        if year is None:
            raise _not_found("Academic year")

        db.query(AcademicYear).filter(
            AcademicYear.school_id == school_id,
            AcademicYear.id != year_id,
        ).update({AcademicYear.is_current: False}, synchronize_session=False)
        year.is_current = True

        if commit:
            db.commit()
            db.refresh(year)
        return year

    # --- terms ----------------------------------------------------------------------------------

    @staticmethod
    def list_terms(school_id: int, db: Session, academic_year_id: int | None = None) -> list[Term]:
        query = (
            db.query(Term)
            .join(AcademicYear, Term.academic_year_id == AcademicYear.id)
            .filter(AcademicYear.school_id == school_id)
        )
        if academic_year_id is not None:
            query = query.filter(Term.academic_year_id == academic_year_id)
        return query.order_by(AcademicYear.starts_on.desc(), Term.sequence).all()

    @staticmethod
    def current_term(school_id: int, db: Session) -> Term | None:
        """The one ACTIVE term in the current year - what every list in the app defaults to.

        Returns None rather than guessing when nothing is active: a caller showing "no current
        term, open one" is far better than one silently showing last year's data.
        """
        year = AcademicService.current_year(school_id, db)
        if year is None:
            return None
        return (
            db.query(Term)
            .filter(Term.academic_year_id == year.id, Term.status == "ACTIVE")
            .order_by(Term.sequence)
            .first()
        )

    @staticmethod
    def _year_for_school(year_id: int, school_id: int, db: Session) -> AcademicYear:
        year = (
            db.query(AcademicYear)
            .filter(AcademicYear.id == year_id, AcademicYear.school_id == school_id)
            .first()
        )
        if year is None:
            raise _not_found("Academic year")
        return year

    @staticmethod
    def create_term(academic_year_id: int, name: str, sequence: int,
                    starts_on: date, ends_on: date, school_id: int, db: Session) -> Term:
        AcademicService._year_for_school(academic_year_id, school_id, db)

        if ends_on <= starts_on:
            raise HTTPException(status_code=400, detail="A term must end after it starts.")

        clash = (
            db.query(Term)
            .filter(Term.academic_year_id == academic_year_id, Term.sequence == sequence)
            .first()
        )
        if clash is not None:
            raise HTTPException(
                status_code=400,
                detail=f"This year already has a term at position {sequence} ('{clash.name}').",
            )

        term = Term(
            academic_year_id=academic_year_id, name=name, sequence=sequence,
            starts_on=starts_on, ends_on=ends_on, status="PLANNED",
        )
        db.add(term)
        db.commit()
        db.refresh(term)
        return term

    @staticmethod
    def get_term(term_id: int, school_id: int, db: Session) -> Term:
        term = (
            db.query(Term)
            .join(AcademicYear, Term.academic_year_id == AcademicYear.id)
            .filter(Term.id == term_id, AcademicYear.school_id == school_id)
            .first()
        )
        if term is None:
            raise _not_found("Term")
        return term

    @staticmethod
    def set_term_status(term_id: int, status: str, school_id: int, db: Session) -> Term:
        if status not in TERM_STATUSES:
            raise HTTPException(status_code=400, detail=f"status must be one of {list(TERM_STATUSES)}.")

        term = AcademicService.get_term(term_id, school_id, db)
        if status == term.status:
            return term

        if status not in TERM_TRANSITIONS[term.status]:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"A {term.status} term cannot become {status}. "
                    f"Allowed from here: {sorted(TERM_TRANSITIONS[term.status])}."
                ),
            )

        # Only one term runs at a time. Activating another closes nothing automatically - that
        # would silently end a term someone is still teaching - so it is refused instead.
        if status == "ACTIVE":
            running = (
                db.query(Term)
                .filter(
                    Term.academic_year_id == term.academic_year_id,
                    Term.status == "ACTIVE",
                    Term.id != term.id,
                )
                .first()
            )
            if running is not None:
                raise HTTPException(
                    status_code=400,
                    detail=f"'{running.name}' is still active. Close it before activating another term.",
                )

        if status == "CLOSED":
            # Closing finalises the class lists rather than leaving them looking current forever.
            db.query(Enrollment).filter(
                Enrollment.section_id.in_(
                    db.query(Section.id).filter(Section.term_id == term.id)
                ),
                Enrollment.status == ACTIVE_ENROLLMENT,
            ).update({Enrollment.status: "COMPLETED"}, synchronize_session=False)

        term.status = status
        db.commit()
        db.refresh(term)
        return term

    # --- sections -------------------------------------------------------------------------------

    @staticmethod
    def list_sections(school_id: int, db: Session, term_id: int | None = None,
                      instructor_id: int | None = None) -> list[Section]:
        query = (
            db.query(Section)
            .join(Term, Section.term_id == Term.id)
            .join(AcademicYear, Term.academic_year_id == AcademicYear.id)
            .filter(AcademicYear.school_id == school_id)
        )
        if term_id is not None:
            query = query.filter(Section.term_id == term_id)
        if instructor_id is not None:
            query = query.filter(Section.instructor_id == instructor_id)
        return query.order_by(Section.id).all()

    @staticmethod
    def create_section(subject_id: int, term_id: int, instructor_id: int, code: str,
                       school_id: int, db: Session,
                       capacity: int | None = None, schedule: str | None = None) -> Section:
        term = AcademicService.get_term(term_id, school_id, db)
        if term.status == "CLOSED":
            raise HTTPException(
                status_code=400,
                detail=f"'{term.name}' is closed. Reopen it before adding sections.",
            )

        # Cross-tenant guard: a subject id or instructor id from another school must not be
        # attachable to this school's term just because the ids happen to exist.
        subject = (
            db.query(Subject)
            .join(Course, Subject.course_id == Course.id)
            .filter(Subject.id == subject_id, Course.school_id == school_id)
            .first()
        )
        if subject is None:
            raise _not_found("Subject")

        instructor = (
            db.query(Instructor)
            .join(User, Instructor.user_id == User.id)
            .filter(Instructor.id == instructor_id, User.school_id == school_id)
            .first()
        )
        if instructor is None:
            raise _not_found("Instructor")

        clash = (
            db.query(Section)
            .filter(
                Section.subject_id == subject_id,
                Section.term_id == term_id,
                Section.code == code,
            )
            .first()
        )
        if clash is not None:
            raise HTTPException(
                status_code=400,
                detail=f"{subject.code} section '{code}' already exists in {term.name}.",
            )

        section = Section(
            subject_id=subject_id, term_id=term_id, instructor_id=instructor_id,
            code=code, capacity=capacity, schedule=schedule,
        )
        db.add(section)
        db.commit()
        db.refresh(section)
        return section

    @staticmethod
    def get_section(section_id: int, school_id: int, db: Session) -> Section:
        section = (
            db.query(Section)
            .join(Term, Section.term_id == Term.id)
            .join(AcademicYear, Term.academic_year_id == AcademicYear.id)
            .filter(Section.id == section_id, AcademicYear.school_id == school_id)
            .first()
        )
        if section is None:
            raise _not_found("Section")
        return section

    # --- enrolment ------------------------------------------------------------------------------

    @staticmethod
    def roster(section_id: int, school_id: int, db: Session,
               active_only: bool = True) -> list[Enrollment]:
        """The class list. This is what an exam roster inherits."""
        AcademicService.get_section(section_id, school_id, db)
        query = db.query(Enrollment).filter(Enrollment.section_id == section_id)
        if active_only:
            query = query.filter(Enrollment.status == ACTIVE_ENROLLMENT)
        return query.order_by(Enrollment.id).all()

    @staticmethod
    def enroll(section_id: int, student_ids: list[int], school_id: int, db: Session) -> dict:
        """Adds students to a section, reporting what changed rather than failing on duplicates.

        Re-running the same enrolment - re-uploading an edited class list, say - must be safe, so
        an already-enrolled student is 'skipped', and a previously DROPPED one is reinstated
        rather than rejected as a duplicate.
        """
        section = AcademicService.get_section(section_id, school_id, db)
        if section.term.status == "CLOSED":
            raise HTTPException(
                status_code=400,
                detail=f"'{section.term.name}' is closed. Reopen it before changing enrolment.",
            )

        enrolled, skipped, reinstated, errors = 0, 0, 0, []

        for student_id in student_ids:
            student = (
                db.query(Student)
                .join(User, Student.user_id == User.id)
                .filter(Student.id == student_id, User.school_id == school_id)
                .first()
            )
            if student is None:
                errors.append(f"student #{student_id} is not in this school")
                continue

            existing = (
                db.query(Enrollment)
                .filter(
                    Enrollment.section_id == section_id,
                    Enrollment.student_id == student_id,
                )
                .first()
            )
            if existing is not None:
                if existing.status == ACTIVE_ENROLLMENT:
                    skipped += 1
                else:
                    existing.status = ACTIVE_ENROLLMENT
                    reinstated += 1
                continue

            db.add(Enrollment(section_id=section_id, student_id=student_id))
            enrolled += 1

        db.commit()
        return {
            "enrolled": enrolled,
            "reinstated": reinstated,
            "skipped_already_enrolled": skipped,
            "errors": errors,
        }

    @staticmethod
    def set_enrollment_status(section_id: int, student_id: int, status: str,
                              school_id: int, db: Session) -> Enrollment:
        if status not in ENROLLMENT_STATUSES:
            raise HTTPException(
                status_code=400, detail=f"status must be one of {list(ENROLLMENT_STATUSES)}."
            )

        AcademicService.get_section(section_id, school_id, db)
        enrollment = (
            db.query(Enrollment)
            .filter(Enrollment.section_id == section_id, Enrollment.student_id == student_id)
            .first()
        )
        if enrollment is None:
            raise _not_found("Enrollment")

        # Dropped rather than deleted: the row is what gives their existing attempts and
        # violations a coherent context, and removing it would orphan that history.
        enrollment.status = status
        db.commit()
        db.refresh(enrollment)
        return enrollment
