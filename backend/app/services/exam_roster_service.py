from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.enrollment import ACTIVE_ENROLLMENT, Enrollment
from app.models.exam import Exam
from app.models.exam_roster import ExamRoster
from app.models.student import Student
from app.models.subject import Subject
from app.schemas.exam_roster import ExamRosterCreate


class ExamRosterService:

    @staticmethod
    def get_all_for_exam(exam: Exam, db: Session):

        return (
            db.query(ExamRoster)
            .filter(ExamRoster.exam_id == exam.id)
            .all()
        )

    @staticmethod
    def get_roster_entry(exam: Exam, student_id: int, db: Session):

        entry = (
            db.query(ExamRoster)
            .filter(ExamRoster.exam_id == exam.id, ExamRoster.student_id == student_id)
            .first()
        )

        if entry is None:
            raise HTTPException(
                status_code=404,
                detail="Roster entry not found for this exam."
            )

        return entry

    @staticmethod
    def add_student(exam: Exam, request: ExamRosterCreate, db: Session):

        student = (
            db.query(Student)
            .filter(Student.id == request.student_id)
            .first()
        )

        if student is None:
            raise HTTPException(
                status_code=404,
                detail="Student not found."
            )

        subject = (
            db.query(Subject)
            .filter(Subject.id == exam.subject_id)
            .first()
        )

        if subject is None or student.course_id != subject.course_id:
            raise HTTPException(
                status_code=400,
                detail="Student is not enrolled in this exam's course."
            )

        existing = (
            db.query(ExamRoster)
            .filter(ExamRoster.exam_id == exam.id, ExamRoster.student_id == student.id)
            .first()
        )

        if existing is not None:
            raise HTTPException(
                status_code=400,
                detail="Student is already on this exam's roster."
            )

        entry = ExamRoster(exam_id=exam.id, student_id=student.id)

        db.add(entry)
        db.commit()
        db.refresh(entry)

        return entry

    @staticmethod
    def remove_student(exam: Exam, student_id: int, db: Session):

        entry = ExamRosterService.get_roster_entry(exam, student_id, db)

        db.delete(entry)
        db.commit()

        return {
            "message": "Student removed from exam roster."
        }

    @staticmethod
    def get_available_students(exam: Exam, db: Session):

        subject = (
            db.query(Subject)
            .filter(Subject.id == exam.subject_id)
            .first()
        )

        if subject is None:
            raise HTTPException(
                status_code=404,
                detail="Subject not found for this exam."
            )

        rostered_ids = (
            db.query(ExamRoster.student_id)
            .filter(ExamRoster.exam_id == exam.id)
        )

        return (
            db.query(Student)
            .filter(Student.course_id == subject.course_id)
            .filter(Student.id.notin_(rostered_ids))
            .all()
        )

    @staticmethod
    def add_all_available(exam: Exam, db: Session):
        """Roster this exam's CLASS - the students enrolled in its section.

        This used to add every student in the exam's COURSE, which was right when a course was the
        widest thing an exam could be scoped to. Roster inheritance made it wrong in two ways at
        once, and one click did both: it rosters people who are not in this class, and because
        precedence is per-exam, the moment any row exists the section's own enrolment stops
        applying. An instructor with a healthy inherited class of three, in a course of five,
        pressed "Add All" and silently ended up admitting five.

        Scoped to the section, the action is what its name suggests and is safe: it admits exactly
        who the exam already admitted, just explicitly - which is the useful starting point for
        narrowing to a makeup or a deferred sitting.

        Adding somebody outside the class is still possible one at a time from the available list,
        which is where a deliberate exception belongs rather than in a bulk button.
        """
        rostered_ids = db.query(ExamRoster.student_id).filter(ExamRoster.exam_id == exam.id)

        classmates = (
            db.query(Enrollment.student_id)
            .filter(
                Enrollment.section_id == exam.section_id,
                Enrollment.status == ACTIVE_ENROLLMENT,
                Enrollment.student_id.notin_(rostered_ids),
            )
            .all()
        )

        entries = [ExamRoster(exam_id=exam.id, student_id=sid) for (sid,) in classmates]
        db.add_all(entries)
        db.commit()

        return {
            "added_count": len(entries)
        }
