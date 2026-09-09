from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_admin
from app.core.database import get_db
from app.models.enrollment import ACTIVE_ENROLLMENT, Enrollment
from app.models.section import Section
from app.models.user import User
from app.schemas.academic import (
    AcademicYearCreate,
    AcademicYearResponse,
    EnrollRequest,
    EnrollResponse,
    EnrollmentResponse,
    EnrollmentStatusRequest,
    SectionCreate,
    SectionResponse,
    TermCreate,
    TermResponse,
    TermStatusRequest,
)
from app.services.academic_service import AcademicService

router = APIRouter(prefix="/academic", tags=["Academic"])


def _school_id(user: User) -> int:
    """The acting user's own school, never a value from the request body.

    Same reasoning as the bulk-import service: a school id arriving in a payload is an invitation
    to write into somebody else's school. Deliberately NOT effective_school_id() either - that
    returns None for a super admin, which is correct for read-only scoping and wrong for anything
    that creates rows (it would produce records belonging to no school at all).
    """
    return user.school_id


# --- academic years ---------------------------------------------------------------------------
# Literal paths before any {param} route - a param route registered first silently swallows them.

@router.get("/years", response_model=list[AcademicYearResponse])
def list_years(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return AcademicService.list_years(_school_id(current_user), db)


@router.get("/years/current", response_model=AcademicYearResponse | None)
def current_year(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return AcademicService.current_year(_school_id(current_user), db)


@router.post("/years", response_model=AcademicYearResponse, status_code=201)
def create_year(
    request: AcademicYearCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return AcademicService.create_year(
        request.label, request.starts_on, request.ends_on, request.make_current,
        _school_id(current_user), db,
    )


@router.put("/years/{year_id}/current", response_model=AcademicYearResponse)
def set_current_year(
    year_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return AcademicService.set_current_year(year_id, _school_id(current_user), db)


# --- terms ------------------------------------------------------------------------------------

@router.get("/terms", response_model=list[TermResponse])
def list_terms(
    academic_year_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return AcademicService.list_terms(_school_id(current_user), db, academic_year_id)


@router.get("/terms/current", response_model=TermResponse | None)
def current_term(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """What every "current" view in the app defaults to. Null when nothing is active, so a client
    can say "no current term, open one" rather than silently showing last year's data."""
    return AcademicService.current_term(_school_id(current_user), db)


@router.post("/terms", response_model=TermResponse, status_code=201)
def create_term(
    request: TermCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return AcademicService.create_term(
        request.academic_year_id, request.name, request.sequence,
        request.starts_on, request.ends_on, _school_id(current_user), db,
    )


@router.put("/terms/{term_id}/status", response_model=TermResponse)
def set_term_status(
    term_id: int,
    request: TermStatusRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return AcademicService.set_term_status(term_id, request.status, _school_id(current_user), db)


# --- sections ---------------------------------------------------------------------------------

def _section_payload(section: Section, db: Session) -> SectionResponse:
    subject = section.subject
    course = subject.course if subject is not None else None
    term = section.term
    instructor = section.instructor
    enrolled = (
        db.query(Enrollment)
        .filter(Enrollment.section_id == section.id, Enrollment.status == ACTIVE_ENROLLMENT)
        .count()
    )
    return SectionResponse(
        id=section.id,
        subject_id=section.subject_id,
        term_id=section.term_id,
        instructor_id=section.instructor_id,
        code=section.code,
        capacity=section.capacity,
        schedule=section.schedule,
        label=section.label,
        subject_code=subject.code if subject else None,
        subject_name=subject.name if subject else None,
        course_code=course.code if course else None,
        term_name=term.name if term else None,
        academic_year_label=term.academic_year.label if term and term.academic_year else None,
        instructor_name=instructor.instructor_name if instructor else None,
        enrolled_count=enrolled,
    )


@router.get("/sections", response_model=list[SectionResponse])
def list_sections(
    term_id: int | None = None,
    instructor_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sections = AcademicService.list_sections(
        _school_id(current_user), db, term_id=term_id, instructor_id=instructor_id
    )
    return [_section_payload(s, db) for s in sections]


@router.post("/sections", response_model=SectionResponse, status_code=201)
def create_section(
    request: SectionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    section = AcademicService.create_section(
        request.subject_id, request.term_id, request.instructor_id, request.code,
        _school_id(current_user), db, capacity=request.capacity, schedule=request.schedule,
    )
    return _section_payload(section, db)


@router.get("/sections/{section_id}", response_model=SectionResponse)
def get_section(
    section_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _section_payload(
        AcademicService.get_section(section_id, _school_id(current_user), db), db
    )


# --- enrolment --------------------------------------------------------------------------------

@router.get("/sections/{section_id}/roster", response_model=list[EnrollmentResponse])
def section_roster(
    section_id: int,
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """The class list an exam roster will inherit."""
    rows = AcademicService.roster(section_id, _school_id(current_user), db, active_only=active_only)
    return [
        EnrollmentResponse(
            id=e.id, section_id=e.section_id, student_id=e.student_id,
            status=e.status, enrolled_at=e.enrolled_at,
            student_name=e.student.student_name if e.student else None,
            student_number=e.student.student_number if e.student else None,
        )
        for e in rows
    ]


@router.post("/sections/{section_id}/enroll", response_model=EnrollResponse)
def enroll_students(
    section_id: int,
    request: EnrollRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return AcademicService.enroll(
        section_id, request.student_ids, _school_id(current_user), db
    )


@router.put("/sections/{section_id}/enrollment/{student_id}", response_model=EnrollmentResponse)
def set_enrollment_status(
    section_id: int,
    student_id: int,
    request: EnrollmentStatusRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    enrollment = AcademicService.set_enrollment_status(
        section_id, student_id, request.status, _school_id(current_user), db
    )
    return EnrollmentResponse(
        id=enrollment.id, section_id=enrollment.section_id, student_id=enrollment.student_id,
        status=enrollment.status, enrolled_at=enrollment.enrolled_at,
        student_name=enrollment.student.student_name if enrollment.student else None,
        student_number=enrollment.student.student_number if enrollment.student else None,
    )
