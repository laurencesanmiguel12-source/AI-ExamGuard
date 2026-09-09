from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import is_super_admin
from app.models.course import Course
from app.models.exam import Exam
from app.models.enrollment import ACTIVE_ENROLLMENT, Enrollment
from app.models.exam_roster import ExamRoster
from app.models.instructor import Instructor
from app.models.instructor_subject import InstructorSubject
from app.models.student import Student
from app.models.subject import Subject
from app.models.user import User
from app.schemas.exam import ExamCreate, ExamUpdate


class ExamService:

    @staticmethod
    def _require_subject_assignment(instructor_id: int, subject_id: int, db: Session) -> None:
        assigned = (
            db.query(InstructorSubject)
            .filter(
                InstructorSubject.instructor_id == instructor_id,
                InstructorSubject.subject_id == subject_id,
            )
            .first()
        )
        if assigned is None:
            raise HTTPException(
                status_code=403,
                detail="Instructor is not assigned to this subject."
            )

    @staticmethod
    def has_explicit_roster(exam: Exam, db: Session) -> bool:
        """Whether anyone has been rostered onto this exam by hand.

        The presence of ANY explicit row - not the presence of this particular student's - is what
        decides which source governs. Otherwise an instructor who rosters five students for a
        makeup sitting would find the section's other forty silently eligible too, because each
        of them individually has no explicit row.
        """
        return (
            db.query(ExamRoster).filter(ExamRoster.exam_id == exam.id).first() is not None
        )

    @staticmethod
    def is_student_eligible(student: Student, exam: Exam, db: Session) -> bool:
        """Who may sit this exam.

        Two sources, in strict priority order:

        1. An EXPLICIT roster, if one exists at all. An instructor who rosters anybody has said
           precisely who sits this exam - a makeup, a deferred sitting, a subset - and that
           statement must not be widened by inheritance.
        2. Otherwise the exam's SECTION ENROLMENT: the class list. This is the normal case, and
           the reason a roster no longer has to be typed in for every exam.

        The 2026-08-20 policy is preserved exactly: an exam with neither an explicit roster nor
        any section enrolment admits NOBODY. It is deliberately not "no roster means course-wide"
        - live feedback was that a newly self-registered student seeing every unrostered course
        exam was the wrong default for this deployment.

        **The migration hazard this had to avoid.** That policy plus inheritance is how a whole
        class gets locked out on exam day: an exam moved onto a section whose enrolment is empty
        would look correctly configured and admit no one. The empty case is therefore surfaced,
        not silent - see ExamService.roster_source, which the roster screen warns from.
        """
        if ExamService.has_explicit_roster(exam, db):
            # Course membership still gates the explicit path, unchanged - it is the safety net
            # for a hand-built list, where a mistyped id is a real possibility.
            subject = db.query(Subject).filter(Subject.id == exam.subject_id).first()
            if subject is None or subject.course_id != student.course_id:
                return False
            return (
                db.query(ExamRoster)
                .filter(ExamRoster.exam_id == exam.id, ExamRoster.student_id == student.id)
                .first()
                is not None
            )

        if exam.section_id is None:
            return False

        # No course check on this path, deliberately. Enrolling a student in a section is an
        # explicit administrative act naming that exact student, which is a stronger statement
        # than "belongs to the same programme" - and cross-programme enrolment (an elective, a
        # cross-enrolled student) is normal at a university. Requiring both would reject those
        # students from an exam they were deliberately enrolled for.
        return (
            db.query(Enrollment)
            .filter(
                Enrollment.section_id == exam.section_id,
                Enrollment.student_id == student.id,
                Enrollment.status == ACTIVE_ENROLLMENT,
            )
            .first()
            is not None
        )

    @staticmethod
    def roster_source(exam: Exam, db: Session) -> dict:
        """Where this exam's roster comes from, and how many it admits.

        Exists so the roster screen can say which of the two sources is in force and warn when
        the answer is "nobody" - the lockout case above is invisible otherwise, because an exam
        with an empty inherited roster looks exactly like a correctly configured one.
        """
        if ExamService.has_explicit_roster(exam, db):
            count = db.query(ExamRoster).filter(ExamRoster.exam_id == exam.id).count()
            return {"source": "EXPLICIT", "count": count, "admits_nobody": count == 0}

        if exam.section_id is None:
            return {"source": "NONE", "count": 0, "admits_nobody": True}

        count = (
            db.query(Enrollment)
            .filter(
                Enrollment.section_id == exam.section_id,
                Enrollment.status == ACTIVE_ENROLLMENT,
            )
            .count()
        )
        return {"source": "SECTION", "count": count, "admits_nobody": count == 0}

    @staticmethod
    def get_all(current_user: User, db: Session):

        if current_user.role.name.lower() != "student":
            # Previously db.query(Exam).all() - every exam in the entire deployment, with zero
            # scoping. Harmless in the single-school world this was written in; a direct
            # cross-tenant leak the moment a second school shares this deployment. Super admin
            # deliberately skips the filter - that's its one legitimate use.
            query = (
                db.query(Exam)
                .join(Subject, Exam.subject_id == Subject.id)
                .join(Course, Subject.course_id == Course.id)
            )
            if not is_super_admin(current_user):
                query = query.filter(Course.school_id == current_user.school_id)

            # Instructors get only their own exams. Every exam *action* is owner-gated by
            # require_exam_owner, so listing the whole school's exams to an instructor promised
            # access the detail routes then refused: Exams.jsx renders a "View roster" link on
            # every row, and a newly created instructor (who owns nothing yet) saw a full list
            # where every single roster link 403'd. Reported live as "new instructor cannot see
            # student roster". Admins still get the whole school - they legitimately manage all
            # of it - and the instructor dashboard already filtered to instructor_id == me.
            if current_user.role.name.lower() == "instructor":
                instructor = (
                    db.query(Instructor)
                    .filter(Instructor.user_id == current_user.id)
                    .first()
                )
                if instructor is None:
                    return []
                query = query.filter(Exam.instructor_id == instructor.id)

            return query.all()

        student = db.query(Student).filter(Student.user_id == current_user.id).first()
        if student is None:
            return []

        course_wide_candidates = (
            db.query(Exam)
            .join(Subject, Exam.subject_id == Subject.id)
            .filter(Subject.course_id == student.course_id)
            .all()
        )

        return [
            exam for exam in course_wide_candidates
            if ExamService.is_student_eligible(student, exam, db)
        ]

    @staticmethod
    def get_by_id(exam_id: int, db: Session):

        exam = (
            db.query(Exam)
            .filter(Exam.id == exam_id)
            .first()
        )

        if exam is None:
            raise HTTPException(
                status_code=404,
                detail="Exam not found."
            )

        return exam

    @staticmethod
    def get_by_id_for_user(exam_id: int, current_user: User, db: Session):

        exam = ExamService.get_by_id(exam_id, db)

        if current_user.role.name.lower() == "student":
            student = db.query(Student).filter(Student.user_id == current_user.id).first()
            if student is None or not ExamService.is_student_eligible(student, exam, db):
                raise HTTPException(
                    status_code=403,
                    detail="This exam is not available for your course."
                )
        elif not is_super_admin(current_user):
            exam_school_id = (
                db.query(Course.school_id)
                .join(Subject, Subject.course_id == Course.id)
                .filter(Subject.id == exam.subject_id)
                .scalar()
            )
            if exam_school_id != current_user.school_id:
                raise HTTPException(
                    status_code=404,
                    detail="Exam not found."
                )

        return exam

    @staticmethod
    def _section_for_instructor(section_id: int, instructor: Instructor, db: Session):
        """The section, if this instructor may actually set an exam on it.

        Ownership is the point of a section: it names exactly one instructor. Until now the
        permission layer had to approximate this through subject assignment, which is why two
        instructors sharing a subject could each reach the other's work. Here it is a direct
        check - you own the class or you do not.
        """
        from app.models.section import Section

        section = db.query(Section).filter(Section.id == section_id).first()
        if section is None:
            raise HTTPException(status_code=404, detail="Section not found.")

        if section.instructor_id != instructor.id:
            raise HTTPException(
                status_code=403,
                detail="That section is taught by another instructor.",
            )

        if section.term is not None and section.term.status == "CLOSED":
            raise HTTPException(
                status_code=400,
                detail=f"'{section.term.name}' is closed. Reopen it before adding exams.",
            )

        return section

    @staticmethod
    def create(instructor: Instructor, request: ExamCreate, db: Session):

        subject = (
            db.query(Subject)
            .filter(Subject.id == request.subject_id)
            .first()
        )

        if subject is None:
            raise HTTPException(
                status_code=404,
                detail="Subject not found."
            )

        ExamService._require_subject_assignment(instructor.id, subject.id, db)

        # instructor_id is always the caller's own instructor record, never taken from the
        # request body - see backend/app/auth/instructor_context.py's get_current_instructor.
        exam_data = request.model_dump(exclude={"instructor_id"})

        # A section, when given, is authoritative for subject as well - it already names one, and
        # letting the body disagree would let an exam claim a section of CS-101 while filing
        # itself under a different subject entirely. Deriving instead of validating means the two
        # cannot drift apart at all.
        section_id = exam_data.get("section_id")
        if section_id is not None:
            section = ExamService._section_for_instructor(section_id, instructor, db)
            exam_data["subject_id"] = section.subject_id

        exam = Exam(**exam_data, instructor_id=instructor.id)

        db.add(exam)
        db.commit()
        db.refresh(exam)

        return exam

    @staticmethod
    def update(exam_id: int, request: ExamUpdate, db: Session):

        exam = ExamService.get_by_id(exam_id, db)

        update_data = request.model_dump(exclude_unset=True)

        if "subject_id" in update_data and update_data["subject_id"] != exam.subject_id:
            ExamService._require_subject_assignment(exam.instructor_id, update_data["subject_id"], db)

        for key, value in update_data.items():
            setattr(exam, key, value)

        db.commit()
        db.refresh(exam)

        return exam

    @staticmethod
    def delete(exam_id: int, db: Session):

        exam = ExamService.get_by_id(exam_id, db)

        db.delete(exam)
        db.commit()

        return {
            "message": "Exam deleted successfully."
        }
