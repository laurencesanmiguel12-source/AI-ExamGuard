from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.choice import Choice
from app.models.exam_session import ExamSession
from app.models.question import Question
from app.models.student_answer import StudentAnswer
from app.schemas.student_answer import (
    StudentAnswerCreate,
)


class StudentAnswerService:

    @staticmethod
    def save_answer(
            session_id: int,
            request: StudentAnswerCreate,
            db: Session
    ):

        session = (
            db.query(ExamSession)
            .filter(
                ExamSession.id == session_id
            )
            .first()
        )

        if session is None:
            raise HTTPException(
                status_code=404,
                detail="Exam session not found."
            )

        if session.status != "IN_PROGRESS":
            raise HTTPException(
                status_code=400,
                detail="Exam session is already submitted."
            )

        question = (
            db.query(Question)
            .filter(
                Question.id == request.question_id,
                Question.exam_id == session.exam_id
            )
            .first()
        )

        if question is None:
            raise HTTPException(
                status_code=404,
                detail="Question not found."
            )

        existing_answer = (
            db.query(StudentAnswer)
            .filter(
                StudentAnswer.exam_session_id == session_id,
                StudentAnswer.question_id == request.question_id
            )
            .first()
        )

        is_correct = False
        points_awarded = 0

        if request.choice_id is not None:

            choice = (
                db.query(Choice)
                .filter(
                    Choice.id == request.choice_id,
                    Choice.question_id == request.question_id
                )
                .first()
            )

            if choice is None:
                raise HTTPException(
                    status_code=404,
                    detail="Choice not found."
                )

            is_correct = choice.is_correct

            if is_correct:
                points_awarded = question.points

        if existing_answer:

            existing_answer.choice_id = request.choice_id
            existing_answer.answer_text = None
            existing_answer.is_correct = is_correct
            existing_answer.points_awarded = points_awarded

            db.commit()
            db.refresh(existing_answer)

            return existing_answer

        answer = StudentAnswer(
            exam_session_id=session_id,
            question_id=request.question_id,
            choice_id=request.choice_id,
            answer_text=None,
            is_correct=is_correct,
            points_awarded=points_awarded
        )

        db.add(answer)
        db.commit()
        db.refresh(answer)

        return answer

    @staticmethod
    def get_answers(
        session_id: int,
        db: Session
    ):

        return (
            db.query(StudentAnswer)
            .filter(
                StudentAnswer.exam_session_id == session_id
            )
            .all()
        )