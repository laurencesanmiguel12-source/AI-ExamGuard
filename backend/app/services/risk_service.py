from collections import Counter
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.exam_session import ExamSession
from app.models.violation import Violation

WEIGHTS = {
    "TAB_SWITCH": 15,
    "FULLSCREEN_EXIT": 20,
    "COPY_PASTE": 10,
    "RIGHT_CLICK": 5,
    "FACE_LOST": 25,
    "IDENTITY_MISMATCH": 30,
    "PHONE_DETECTED": 30,
    "MULTIPLE_PEOPLE": 25,
    "AI_TOOL_DETECTED": 40,
    "SEARCH_ENGINE_DETECTED": 35,
}

WINDOW_SECONDS = 120


def _score(violations):
    total = sum(WEIGHTS.get(v.event_type, 0) for v in violations)
    return float(min(100, total))


class RiskService:

    @staticmethod
    def compute_risk(
        session_id: int,
        db: Session
    ) -> float:

        cutoff = datetime.now(timezone.utc) - timedelta(seconds=WINDOW_SECONDS)

        violations = (
            db.query(Violation)
            .filter(
                Violation.exam_session_id == session_id,
                Violation.created_at >= cutoff
            )
            .all()
        )

        return _score(violations)

    @staticmethod
    def get_live_sessions(db: Session):

        sessions = (
            db.query(ExamSession)
            .filter(ExamSession.status == "IN_PROGRESS")
            .all()
        )

        if not sessions:
            return {
                "sessions": [],
                "recent_events": []
            }

        session_ids = [s.id for s in sessions]
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=WINDOW_SECONDS)

        all_violations = (
            db.query(Violation)
            .filter(Violation.exam_session_id.in_(session_ids))
            .order_by(Violation.created_at.desc())
            .all()
        )

        violations_by_session = {}
        for v in all_violations:
            violations_by_session.setdefault(v.exam_session_id, []).append(v)

        session_payload = []
        for s in sessions:
            session_violations = violations_by_session.get(s.id, [])
            windowed = [v for v in session_violations if v.created_at >= cutoff]

            session_payload.append({
                "session_id": s.id,
                "student_id": s.student_id,
                "student_number": s.student.student_number if s.student else f"#{s.student_id}",
                "exam_id": s.exam_id,
                "exam_title": s.exam.title if s.exam else f"#{s.exam_id}",
                "started_at": s.started_at,
                "risk_score": _score(windowed),
                "violation_counts": dict(Counter(v.event_type for v in session_violations)),
            })

        sessions_by_id = {s.id: s for s in sessions}
        recent_events = [
            {
                "session_id": v.exam_session_id,
                "student_number": (
                    sessions_by_id[v.exam_session_id].student.student_number
                    if sessions_by_id[v.exam_session_id].student
                    else f"#{sessions_by_id[v.exam_session_id].student_id}"
                ),
                "exam_id": sessions_by_id[v.exam_session_id].exam_id,
                "event_type": v.event_type,
                "detail": v.detail,
                "created_at": v.created_at,
            }
            for v in all_violations[:10]
        ]

        return {
            "sessions": session_payload,
            "recent_events": recent_events,
        }
