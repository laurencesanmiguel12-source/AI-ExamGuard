from collections import Counter

from sqlalchemy.orm import Session

from app.models.course import Course
from app.models.exam import Exam
from app.models.exam_session import ExamSession, GRADED_STATUSES
from app.models.instructor import Instructor
from app.models.subject import Subject
from app.models.user import User
from app.models.violation import Violation
from app.services.risk_service import RiskService


class AnalyticsService:

    @staticmethod
    def get_instructor_summary(instructor: Instructor, db: Session):

        exams = (
            db.query(Exam)
            .filter(Exam.instructor_id == instructor.id)
            .all()
        )

        if not exams:
            return {
                "exams": [],
                "total_exams": 0,
                "overall_pass_rate": 0,
                "overall_average_risk_score": 0,
            }

        exam_ids = [e.id for e in exams]

        sessions = (
            db.query(ExamSession)
            .filter(ExamSession.exam_id.in_(exam_ids))
            .all()
        )
        sessions_by_exam = {}
        for s in sessions:
            sessions_by_exam.setdefault(s.exam_id, []).append(s)

        submitted = [s for s in sessions if s.status in GRADED_STATUSES]
        submitted_session_ids = [s.id for s in submitted]

        violations = (
            db.query(Violation)
            .filter(Violation.exam_session_id.in_(submitted_session_ids))
            .all()
            if submitted_session_ids else []
        )
        violations_by_session = {}
        for v in violations:
            violations_by_session.setdefault(v.exam_session_id, []).append(v)

        # Computed once per session (not re-derived per exam/instructor loop) since scoring calls
        # into the fitted vision model - same one-pass-then-reuse shape as report_service.py.
        risk_by_session = {
            s.id: RiskService.score_violations(violations_by_session.get(s.id, []))
            for s in submitted
        }

        exam_summaries = []
        for exam in exams:
            exam_submitted = [
                s for s in sessions_by_exam.get(exam.id, [])
                if s.status in GRADED_STATUSES
            ]
            pass_count = sum(1 for s in exam_submitted if s.passed)
            exam_risk_scores = [risk_by_session[s.id] for s in exam_submitted]

            exam_summaries.append({
                "exam_id": exam.id,
                "title": exam.title,
                "submitted_count": len(exam_submitted),
                "pass_rate": (pass_count / len(exam_submitted) * 100) if exam_submitted else 0,
                "average_percentage": (
                    sum(s.percentage for s in exam_submitted) / len(exam_submitted)
                    if exam_submitted else 0
                ),
                "average_risk_score": (
                    sum(exam_risk_scores) / len(exam_risk_scores)
                    if exam_risk_scores else 0
                ),
            })

        total_pass = sum(1 for s in submitted if s.passed)
        all_risk_scores = list(risk_by_session.values())

        return {
            "exams": exam_summaries,
            "total_exams": len(exams),
            "overall_pass_rate": (total_pass / len(submitted) * 100) if submitted else 0,
            "overall_average_risk_score": (
                sum(all_risk_scores) / len(all_risk_scores) if all_risk_scores else 0
            ),
        }

    @staticmethod
    def get_school_summary(school_id: int, db: Session):

        exams = (
            db.query(Exam)
            .join(Subject, Exam.subject_id == Subject.id)
            .join(Course, Subject.course_id == Course.id)
            .filter(Course.school_id == school_id)
            .all()
        )
        instructors = (
            db.query(Instructor)
            .join(User, Instructor.user_id == User.id)
            .filter(User.school_id == school_id)
            .all()
        )

        def instructor_name(instructor):
            return f"{instructor.user.first_name} {instructor.user.last_name}" if instructor.user else f"#{instructor.id}"

        if not exams:
            return {
                "total_exams": 0,
                "aggregate_pass_rate": 0,
                "aggregate_average_risk_score": 0,
                "total_violations": 0,
                "violation_breakdown": {},
                "instructors": [
                    {
                        "instructor_id": i.id,
                        "instructor_name": instructor_name(i),
                        "exam_count": 0,
                        "avg_pass_rate": 0,
                        "avg_risk_score": 0,
                    }
                    for i in instructors
                ],
            }

        exam_ids = [e.id for e in exams]
        exams_by_id = {e.id: e for e in exams}
        exam_count_by_instructor = Counter(e.instructor_id for e in exams)

        sessions = (
            db.query(ExamSession)
            .filter(ExamSession.exam_id.in_(exam_ids))
            .all()
        )
        submitted = [s for s in sessions if s.status in GRADED_STATUSES]
        submitted_session_ids = [s.id for s in submitted]

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

        risk_by_session = {
            s.id: RiskService.score_violations(violations_by_session.get(s.id, []))
            for s in submitted
        }

        submitted_by_instructor = {}
        for s in submitted:
            instructor_id = exams_by_id[s.exam_id].instructor_id
            submitted_by_instructor.setdefault(instructor_id, []).append(s)

        instructor_summaries = []
        for instructor in instructors:
            instructor_sessions = submitted_by_instructor.get(instructor.id, [])
            pass_count = sum(1 for s in instructor_sessions if s.passed)
            instructor_risk_scores = [risk_by_session[s.id] for s in instructor_sessions]

            instructor_summaries.append({
                "instructor_id": instructor.id,
                "instructor_name": instructor_name(instructor),
                "exam_count": exam_count_by_instructor.get(instructor.id, 0),
                "avg_pass_rate": (
                    pass_count / len(instructor_sessions) * 100 if instructor_sessions else 0
                ),
                "avg_risk_score": (
                    sum(instructor_risk_scores) / len(instructor_risk_scores)
                    if instructor_risk_scores else 0
                ),
            })

        total_pass = sum(1 for s in submitted if s.passed)
        all_risk_scores = list(risk_by_session.values())

        return {
            "total_exams": len(exams),
            "aggregate_pass_rate": (total_pass / len(submitted) * 100) if submitted else 0,
            "aggregate_average_risk_score": (
                sum(all_risk_scores) / len(all_risk_scores) if all_risk_scores else 0
            ),
            "total_violations": len(violations),
            "violation_breakdown": violation_breakdown,
            "instructors": instructor_summaries,
        }
