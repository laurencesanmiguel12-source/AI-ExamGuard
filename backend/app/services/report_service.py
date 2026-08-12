from collections import Counter

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.exam import Exam
from app.models.exam_session import ExamSession, GRADED_STATUSES
from app.models.question import Question
from app.models.student import Student
from app.models.student_answer import StudentAnswer
from app.models.violation import Violation
from app.services.risk_service import RiskService


class ReportService:

    @staticmethod
    def get_exam_report(
        exam_id: int,
        db: Session
    ):

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

        sessions = (
            db.query(ExamSession)
            .filter(ExamSession.exam_id == exam_id)
            .order_by(ExamSession.started_at.desc())
            .all()
        )

        submitted = [s for s in sessions if s.status in GRADED_STATUSES]

        student_ids = {s.student_id for s in sessions}
        students_by_id = {
            student.id: student
            for student in (
                db.query(Student)
                .filter(Student.id.in_(student_ids))
                .all()
                if student_ids else []
            )
        }

        attempts = [
            {
                "session_id": s.id,
                "student_id": s.student_id,
                "student_number": (
                    students_by_id[s.student_id].student_number
                    if s.student_id in students_by_id
                    else f"#{s.student_id}"
                ),
                "student_name": (
                    (students_by_id[s.student_id].student_name if s.student_id in students_by_id else None)
                    or f"#{s.student_id}"
                ),
                "started_at": s.started_at,
                "submitted_at": s.submitted_at,
                "status": s.status,
                "score": s.score,
                "percentage": s.percentage,
                "passed": s.passed,
            }
            for s in sessions
        ]

        average_score = (
            sum(s.score for s in submitted) / len(submitted)
            if submitted else 0
        )
        average_percentage = (
            sum(s.percentage for s in submitted) / len(submitted)
            if submitted else 0
        )
        pass_count = sum(1 for s in submitted if s.passed)
        fail_count = len(submitted) - pass_count
        pass_rate = (
            (pass_count / len(submitted)) * 100
            if submitted else 0
        )

        questions = (
            db.query(Question)
            .filter(Question.exam_id == exam_id)
            .order_by(Question.order_number)
            .all()
        )

        submitted_session_ids = [s.id for s in submitted]
        answers = (
            db.query(StudentAnswer)
            .filter(StudentAnswer.exam_session_id.in_(submitted_session_ids))
            .all()
            if submitted_session_ids else []
        )

        answers_by_question = {}
        for answer in answers:
            answers_by_question.setdefault(answer.question_id, []).append(answer)

        question_reports = []
        for q in questions:
            qa = answers_by_question.get(q.id, [])
            answered_count = len(qa)
            correct_count = sum(1 for a in qa if a.is_correct)
            accuracy = (
                (correct_count / answered_count) * 100
                if answered_count else 0
            )
            question_reports.append({
                "question_id": q.id,
                "question_text": q.question_text,
                "question_type": q.question_type,
                "points": q.points,
                "answered_count": answered_count,
                "correct_count": correct_count,
                "accuracy": accuracy,
            })

        # Scoped to submitted (graded) attempts only, same population as average_score/pass_rate
        # above - a still-IN_PROGRESS session's violations are already visible on the live monitor
        # (RiskService.get_live_sessions) and shouldn't muddy this exam's "final result" analytics.
        violations = (
            db.query(Violation)
            .filter(Violation.exam_session_id.in_(submitted_session_ids))
            .all()
            if submitted_session_ids else []
        )
        violation_breakdown = dict(Counter(v.event_type for v in violations))

        violations_by_session = {}
        for v in violations:
            violations_by_session.setdefault(v.exam_session_id, []).append(v)

        session_risk_scores = [
            RiskService.score_violations(violations_by_session.get(sid, []))
            for sid in submitted_session_ids
        ]
        average_risk_score = (
            sum(session_risk_scores) / len(session_risk_scores)
            if session_risk_scores else 0
        )
        risk_distribution = {band: 0 for band in ("LOW", "MEDIUM", "HIGH", "CRITICAL")}
        for score in session_risk_scores:
            risk_distribution[RiskService.risk_band(score)] += 1

        return {
            "exam_id": exam.id,
            "title": exam.title,
            "total_points": exam.total_points,
            "passing_score": exam.passing_score,
            "total_attempts": len(sessions),
            "submitted_count": len(submitted),
            "in_progress_count": sum(1 for s in sessions if s.status == "IN_PROGRESS"),
            "average_score": average_score,
            "average_percentage": average_percentage,
            "pass_count": pass_count,
            "fail_count": fail_count,
            "pass_rate": pass_rate,
            "attempts": attempts,
            "questions": question_reports,
            "violation_breakdown": violation_breakdown,
            "average_risk_score": average_risk_score,
            "risk_distribution": risk_distribution,
        }
