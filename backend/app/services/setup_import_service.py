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
from app.models.instructor import Instructor
from app.models.instructor_subject import InstructorSubject
from app.models.subject import Subject
from app.models.user import User
from app.schemas.course import CourseCreate
from app.schemas.instructor import InstructorCreate
from app.schemas.setup_import import SetupImportResponse, SetupImportRowError
from app.schemas.subject import SubjectCreate
from app.services.course_service import CourseService
from app.services.instructor_service import InstructorService
from app.services.subject_service import SubjectService

ROW_TYPES = ("course", "subject", "instructor")

# Dependency order, not file order: a subject may appear above its course in the sheet and should
# still import.
PROCESS_ORDER = ("course", "subject", "instructor")


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

        created = {"course": 0, "subject": 0, "instructor": 0}
        skipped = {"course": 0, "subject": 0, "instructor": 0}

        handlers = {
            "course": SetupImportService._import_course,
            "subject": SetupImportService._import_subject,
            "instructor": SetupImportService._import_instructor,
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
            skipped_existing=sum(skipped.values()),
            errors=errors,
        )

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
