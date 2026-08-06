from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.instructor import Instructor
from app.models.instructor_subject import InstructorSubject
from app.models.subject import Subject
from app.schemas.instructor_subject import InstructorSubjectCreate


class InstructorSubjectService:

    @staticmethod
    def get_all_for_instructor(instructor: Instructor, db: Session):

        return (
            db.query(InstructorSubject)
            .filter(InstructorSubject.instructor_id == instructor.id)
            .all()
        )

    @staticmethod
    def is_assigned(instructor_id: int, subject_id: int, db: Session) -> bool:

        return (
            db.query(InstructorSubject)
            .filter(
                InstructorSubject.instructor_id == instructor_id,
                InstructorSubject.subject_id == subject_id,
            )
            .first()
            is not None
        )

    @staticmethod
    def assign(instructor: Instructor, request: InstructorSubjectCreate, db: Session):

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

        if InstructorSubjectService.is_assigned(instructor.id, subject.id, db):
            raise HTTPException(
                status_code=400,
                detail="Instructor is already assigned to this subject."
            )

        entry = InstructorSubject(instructor_id=instructor.id, subject_id=subject.id)

        db.add(entry)
        db.commit()
        db.refresh(entry)

        return entry

    @staticmethod
    def unassign(instructor: Instructor, subject_id: int, db: Session):

        entry = (
            db.query(InstructorSubject)
            .filter(
                InstructorSubject.instructor_id == instructor.id,
                InstructorSubject.subject_id == subject_id,
            )
            .first()
        )

        if entry is None:
            raise HTTPException(
                status_code=404,
                detail="Instructor is not assigned to this subject."
            )

        db.delete(entry)
        db.commit()

        return {
            "message": "Instructor unassigned from subject."
        }
