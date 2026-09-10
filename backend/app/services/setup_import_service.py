"""Bulk-load a school's academic structure - courses, subjects and instructors - from one CSV.

**Why one file rather than three.** A school that already has this data has it in one place, and
the three entities are not independent: a subject needs its course to exist, and an instructor's
subject assignment needs the subject. Splitting it into three uploads would just make the admin
sequence them by hand, and get it wrong. Rows declare their own `type` and are processed in
dependency order, so a subject can reference a course defined a few rows above it.

**Rows reference each other by code, never by id.** An admin filling this in from a registrar's
spreadsheet knows "BSCS", not database ids - and ids do not exist yet for anything created by the
same file.

**Creation goes through the normal services**, not straight to the ORM. CourseService.create and
friends own the duplicate checks, the school scoping and the "an instructor without a subject
cannot set an exam" rules. Reimplementing any of that here would mean two definitions of correct,
which is how a bulk path quietly becomes the one that lets bad data in.

**Re-running the same file is safe.** A row whose record already exists is reported as skipped,
not as a failure - an admin who adds ten rows to a sheet and re-uploads it should get ten new
records and a note about the rest, not 40 errors.
"""
import csv
import io

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.course import Course
from app.models.academic_year import AcademicYear
from app.models.enrollment import Enrollment
from app.models.instructor import Instructor
from app.models.section import Section
from app.models.student import Student
from app.models.term import Term
from app.models.instructor_subject import InstructorSubject
from app.models.subject import Subject
from app.models.user import User
from app.schemas.course import CourseCreate
from app.schemas.instructor import InstructorCreate
from app.schemas.setup_import import SetupImportResponse, SetupImportRowError
from app.schemas.student import StudentCreate
from app.schemas.subject import SubjectCreate
from app.services.academic_service import AcademicService
from app.services.course_service import CourseService
from app.services.instructor_service import InstructorService
from app.services.student_service import StudentService
from app.services.subject_service import SubjectService

ROW_TYPES = ("course", "subject", "instructor", "student", "section", "enrollment")

# Dependency order, not file order: a subject may appear above its course in the sheet and should
# still import. The chain is longer now - an enrolment needs a section, which needs a subject and
# an instructor, and needs the student to exist to be enrolled at all.
PROCESS_ORDER = ("course", "subject", "instructor", "student", "section", "enrollment")

# Sections and enrolments land in whichever term is RUNNING, rather than naming one in every row.
# A registrar filling this in is describing this semester's classes; asking them to repeat the
# term on three hundred rows invites one of them to disagree with the rest, and the answer to
# "which term" is already an administrative decision made on the Academic Calendar.
_NO_TERM = (
    "no term is running - activate one on the Academic Calendar first, so classes have somewhere "
    "to sit"
)


def _clean(row: dict, key: str) -> str:
    return (row.get(key) or "").strip()


class SetupImportService:

    @staticmethod
    def import_setup(file_bytes: bytes, current_user: User, school_id: int,
                     db: Session) -> SetupImportResponse:
        try:
            text = file_bytes.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="CSV file must be UTF-8 encoded.")

        reader = csv.DictReader(io.StringIO(text))
        if reader.fieldnames is None or "type" not in [
            (f or "").strip().lower() for f in reader.fieldnames
        ]:
            raise HTTPException(
                status_code=400,
                detail="CSV needs a 'type' column saying whether each row is a course, subject "
                       "or instructor. Download the template for the expected columns."
            )

        rows = []
        errors: list[SetupImportRowError] = []
        for i, raw in enumerate(reader):
            row_number = i + 2  # header is row 1
            row_type = _clean(raw, "type").lower()
            if not row_type:
                continue  # a blank spacer line between sections is not an error
            if row_type not in ROW_TYPES:
                errors.append(SetupImportRowError(
                    row=row_number,
                    message=f"type must be one of {list(ROW_TYPES)}, got '{row_type}'",
                ))
                continue
            rows.append((row_number, row_type, raw))

        created = {t: 0 for t in ROW_TYPES}
        skipped = {t: 0 for t in ROW_TYPES}

        handlers = {
            "course": SetupImportService._import_course,
            "subject": SetupImportService._import_subject,
            "instructor": SetupImportService._import_instructor,
            "student": SetupImportService._import_student,
            "section": SetupImportService._import_section,
            "enrollment": SetupImportService._import_enrollment,
        }

        for row_type in PROCESS_ORDER:
            for row_number, this_type, raw in rows:
                if this_type != row_type:
                    continue
                try:
                    outcome = handlers[row_type](raw, current_user, school_id, db)
                except HTTPException as e:
                    # One bad row must not abandon the rest of the file, and a failed create can
                    # leave the session dirty.
                    db.rollback()
                    errors.append(SetupImportRowError(row=row_number, message=str(e.detail)))
                    continue
                except Exception as e:
                    db.rollback()
                    errors.append(SetupImportRowError(row=row_number, message=f"could not import: {e}"))
                    continue

                if outcome == "created":
                    created[row_type] += 1
                else:
                    skipped[row_type] += 1

        return SetupImportResponse(
            created_courses=created["course"],
            created_subjects=created["subject"],
            created_instructors=created["instructor"],
            created_students=created["student"],
            created_sections=created["section"],
            created_enrollments=created["enrollment"],
            skipped_existing=sum(skipped.values()),
            errors=errors,
        )

    @staticmethod
    def preview(file_bytes: bytes, current_user: User, school_id: int,
                db: Session) -> SetupImportResponse:
        """What this file WOULD do, run through the real import and then thrown away.

        The panel asked to see duplicates and bad formatting before anything is written. The
        tempting way to answer that is a second pass that re-checks the rows - and that is exactly
        the "two definitions of correct" this module's docstring warns about: a preview that
        validates differently from the importer is worse than none, because it is trusted.

        So this runs the importer itself, unmodified, against a throwaway session on its own
        connection, and rolls the whole connection back afterwards. Every duplicate check, every
        cross-reference, every per-row error is the real one, because it IS the real one.

        `join_transaction_mode="create_savepoint"` is what makes that work: the services commit as
        they always do, but those commits land on a SAVEPOINT inside the outer transaction rather
        than on the database, so the final rollback still takes all of them. The importer's own
        per-row `db.rollback()` unwinds to that savepoint rather than to the outer transaction,
        which is why one bad row still does not abandon the rest.
        """
        # The caller's OWN connection, not a fresh one from the engine. A second connection would
        # sit outside this request's transaction and so could not see anything it has not
        # committed - which is exactly the state the test harness runs every test in, and would
        # have made the preview disagree with the import for reasons nobody could reproduce
        # locally. Joining here means the preview reads precisely what the import would read.
        connection = db.connection()
        outer = connection.begin_nested()
        preview_db = Session(bind=connection, join_transaction_mode="create_savepoint")
        try:
            result = SetupImportService.import_setup(
                file_bytes, current_user, school_id, preview_db
            )
        finally:
            preview_db.close()
            outer.rollback()
            # The parent session may hold rows that only ever existed inside the savepoint.
            db.expire_all()

        return result.model_copy(update={"preview": True})

    # --- offering layer: students, sections, class lists -----------------------------------------

    @staticmethod
    def _active_term(school_id: int, db: Session) -> Term:
        term = (
            db.query(Term)
            .join(AcademicYear, Term.academic_year_id == AcademicYear.id)
            .filter(AcademicYear.school_id == school_id, Term.status == "ACTIVE")
            .order_by(Term.sequence)
            .first()
        )
        if term is None:
            raise HTTPException(status_code=400, detail=_NO_TERM)
        return term

    @staticmethod
    def _subject_by_code(code: str, school_id: int, db: Session) -> Subject:
        subject = (
            db.query(Subject)
            .join(Course, Subject.course_id == Course.id)
            .filter(Subject.code == code, Course.school_id == school_id)
            .first()
        )
        if subject is None:
            raise HTTPException(
                status_code=400,
                detail=f"no subject with code '{code}' - add it as a subject row first",
            )
        return subject

    @staticmethod
    def _import_student(row, current_user, school_id, db) -> str:
        """Students are identified by EMAIL, not by student number.

        The number is generated on creation (STU00042), so a sheet cannot supply one and cannot
        reference one either - the row that enrols this student has to name them by something the
        person filling in the spreadsheet actually knows.
        """
        email = _clean(row, "email")
        first_name, last_name = _clean(row, "first_name"), _clean(row, "last_name")
        password = _clean(row, "password")
        course_code = _clean(row, "course_code")

        if not email or not first_name or not last_name or not course_code:
            raise HTTPException(
                status_code=400,
                detail="a student row needs email, first_name, last_name and course_code",
            )
        if not password:
            raise HTTPException(
                status_code=400,
                detail="a student row needs a password - the account is created ready to use, so "
                       "tell them to change it after their first sign-in",
            )

        if db.query(User).filter(User.email == email.lower()).first():
            return "skipped"

        course = (
            db.query(Course)
            .filter(Course.code == course_code, Course.school_id == school_id)
            .first()
        )
        if course is None:
            raise HTTPException(
                status_code=400,
                detail=f"no course with code '{course_code}' - add it as a course row, or check "
                       f"the spelling",
            )

        StudentService.create(
            StudentCreate(
                course_id=course.id, email=email, password=password,
                first_name=first_name, last_name=last_name,
            ),
            current_user,
            db,
        )
        return "created"

    @staticmethod
    def _import_section(row, current_user, school_id, db) -> str:
        """One class: a subject, taught by one instructor, in the term that is running."""
        subject_code = _clean(row, "subject_codes")
        employee_number = _clean(row, "employee_number")
        code = _clean(row, "code")

        if not subject_code or not employee_number or not code:
            raise HTTPException(
                status_code=400,
                detail="a section row needs subject_codes (one subject), employee_number and code",
            )

        term = SetupImportService._active_term(school_id, db)
        subject = SetupImportService._subject_by_code(subject_code, school_id, db)

        instructor = (
            db.query(Instructor)
            .join(User, Instructor.user_id == User.id)
            .filter(
                Instructor.employee_number == employee_number,
                User.school_id == school_id,
            )
            .first()
        )
        if instructor is None:
            raise HTTPException(
                status_code=400,
                detail=f"no instructor with employee number '{employee_number}' - add them as an "
                       f"instructor row first",
            )

        existing = (
            db.query(Section)
            .filter(
                Section.subject_id == subject.id,
                Section.term_id == term.id,
                Section.code == code,
            )
            .first()
        )
        if existing is not None:
            return "skipped"

        capacity = _clean(row, "capacity")
        AcademicService.create_section(
            subject.id, term.id, instructor.id, code, school_id, db,
            capacity=int(capacity) if capacity.isdigit() else None,
            schedule=_clean(row, "schedule") or None,
        )
        return "created"

    @staticmethod
    def _import_enrollment(row, current_user, school_id, db) -> str:
        """One student into one class - the rows that decide whether anybody can sit an exam."""
        email = _clean(row, "email")
        subject_code = _clean(row, "subject_codes")
        code = _clean(row, "code")

        if not email or not subject_code or not code:
            raise HTTPException(
                status_code=400,
                detail="an enrollment row needs email, subject_codes (one subject) and code (the "
                       "section)",
            )

        term = SetupImportService._active_term(school_id, db)
        subject = SetupImportService._subject_by_code(subject_code, school_id, db)

        section = (
            db.query(Section)
            .filter(
                Section.subject_id == subject.id,
                Section.term_id == term.id,
                Section.code == code,
            )
            .first()
        )
        if section is None:
            raise HTTPException(
                status_code=400,
                detail=f"no section '{code}' of {subject_code} in {term.name} - add it as a "
                       f"section row first",
            )

        student = (
            db.query(Student)
            .join(User, Student.user_id == User.id)
            .filter(User.email == email.lower(), User.school_id == school_id)
            .first()
        )
        if student is None:
            raise HTTPException(
                status_code=400,
                detail=f"no student with email '{email}' - add them as a student row first",
            )

        already = (
            db.query(Enrollment)
            .filter(
                Enrollment.section_id == section.id,
                Enrollment.student_id == student.id,
                Enrollment.status == "ENROLLED",
            )
            .first()
        )
        if already is not None:
            return "skipped"

        # Through the service, not a raw insert: it owns reinstating a previously DROPPED student
        # rather than colliding with the row that is already there.
        AcademicService.enroll(section.id, [student.id], school_id, db)
        return "created"

    # --- per-type handlers ---------------------------------------------------------------------

    @staticmethod
    def _import_course(row, current_user, school_id, db) -> str:
        code, name = _clean(row, "code"), _clean(row, "name")
        if not code or not name:
            raise HTTPException(status_code=400, detail="a course row needs both code and name")

        if db.query(Course).filter(Course.code == code, Course.school_id == school_id).first():
            return "skipped"

        CourseService.create(CourseCreate(code=code, name=name), school_id, db)
        return "created"

    @staticmethod
    def _import_subject(row, current_user, school_id, db) -> str:
        code, name = _clean(row, "code"), _clean(row, "name")
        course_code = _clean(row, "course_code")
        if not code or not name or not course_code:
            raise HTTPException(
                status_code=400,
                detail="a subject row needs code, name and course_code",
            )

        course = (
            db.query(Course)
            .filter(Course.code == course_code, Course.school_id == school_id)
            .first()
        )
        if course is None:
            raise HTTPException(
                status_code=400,
                detail=f"no course with code '{course_code}' - add it as a course row, or check "
                       f"the spelling",
            )

        if db.query(Subject).filter(
            Subject.course_id == course.id, Subject.code == code
        ).first():
            return "skipped"

        SubjectService.create(
            SubjectCreate(code=code, name=name, course_id=course.id), current_user, db
        )
        return "created"

    @staticmethod
    def _import_instructor(row, current_user, school_id, db) -> str:
        employee_number = _clean(row, "employee_number")
        email = _clean(row, "email")
        first_name, last_name = _clean(row, "first_name"), _clean(row, "last_name")
        password = _clean(row, "password")

        if not employee_number or not email or not first_name or not last_name:
            raise HTTPException(
                status_code=400,
                detail="an instructor row needs employee_number, email, first_name and last_name",
            )
        if not password:
            raise HTTPException(
                status_code=400,
                detail="an instructor row needs a password - the account is created ready to use, "
                       "so tell them to change it after their first sign-in",
            )

        # Either identifier already existing means this instructor is already set up.
        if db.query(User).filter(User.email == email.lower()).first():
            return "skipped"
        if (
            db.query(Instructor)
            .join(User, Instructor.user_id == User.id)
            .filter(Instructor.employee_number == employee_number, User.school_id == school_id)
            .first()
        ):
            return "skipped"

        # Subject codes are resolved to ids here rather than passed through, so the sheet stays
        # readable. Semicolons, because a comma would need the cell quoting in every file.
        subject_ids = []
        raw_codes = _clean(row, "subject_codes")
        for subject_code in [c.strip() for c in raw_codes.split(";") if c.strip()]:
            subject = (
                db.query(Subject)
                .join(Course, Subject.course_id == Course.id)
                .filter(Subject.code == subject_code, Course.school_id == school_id)
                .first()
            )
            if subject is None:
                raise HTTPException(
                    status_code=400,
                    detail=f"no subject with code '{subject_code}' - add it as a subject row first",
                )
            subject_ids.append(subject.id)

        InstructorService.create(
            InstructorCreate(
                employee_number=employee_number,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                subject_ids=subject_ids,
            ),
            current_user,
            db,
        )
        return "created"
