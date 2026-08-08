from collections import Counter
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.course import Course
from app.models.exam import Exam
from app.models.exam_session import ExamSession
from app.models.subject import Subject
from app.models.violation import Violation
from app.services.risk_model_service import RiskModelService

# Behavioral signals only - no video ground truth exists to train these against (they're browser
# events, not something visible in webcam footage), so they stay hand-weighted. FACE_LOST,
# PHONE_DETECTED, and MULTIPLE_PEOPLE used to be weighted here too; they're now scored by
# RiskModelService, a logistic regression trained on real cheat-event ground truth (MSU OEP
# dataset) instead of guessed weights - see backend/training/train_risk_model.py.
WEIGHTS = {
    "TAB_SWITCH": 15,
    "FULLSCREEN_EXIT": 20,
    "COPY_PASTE": 10,
    "RIGHT_CLICK": 5,
    "IDENTITY_MISMATCH": 30,
    "AI_TOOL_DETECTED": 40,
    "SEARCH_ENGINE_DETECTED": 35,
    # Unvalidated, same as face_service.py's underlying pitch/duration thresholds - a geometric
    # head-pose proxy is weaker evidence than a direct visual identification, so this sits below
    # IDENTITY_MISMATCH. (The original plan compared this against PHONE_DETECTED's old weight,
    # but PHONE_DETECTED has since moved to RiskModelService above - IDENTITY_MISMATCH is the
    # current hand-weighted anchor instead.)
    "PROLONGED_HEAD_DOWN": 20,
    # A sustained run of near-identical webcam frames - unlike IDENTITY_MISMATCH (which can be a
    # single bad-lighting/angle frame), this only fires after several consecutive polls show no
    # natural micro-movement at all, which is stronger evidence of a deliberate static photo held
    # to the camera rather than an incidental misread - weighted above IDENTITY_MISMATCH on that
    # basis. Still unvalidated (see face_service.py's STATIC_IMAGE_DIFF_THRESHOLD comment).
    "STATIC_IMAGE_SUSPECTED": 35,
}

VISION_EVENT_TYPES = {
    "FACE_LOST": "face_lost_count",
    "PHONE_DETECTED": "phone_detected_count",
    "MULTIPLE_PEOPLE": "multiple_people_count",
}

WINDOW_SECONDS = 120
TIMELINE_POINTS = 11


def _score(violations):
    # An overturned appeal means the violation was flagged in error - it shouldn't still count
    # against the student's risk score just because the row is never deleted (it stays as the
    # historical record of the appeal decision).
    violations = [v for v in violations if v.appeal_status != "OVERTURNED"]

    behavioral_total = sum(WEIGHTS.get(v.event_type, 0) for v in violations)

    vision_counts = Counter()
    for v in violations:
        feature = VISION_EVENT_TYPES.get(v.event_type)
        if feature:
            vision_counts[feature] += 1

    vision_score = RiskModelService.predict(
        face_lost_count=vision_counts["face_lost_count"],
        phone_detected_count=vision_counts["phone_detected_count"],
        multiple_people_count=vision_counts["multiple_people_count"],
    )

    return float(min(100, behavioral_total + vision_score))


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
    def get_session_summary(session: ExamSession, db: Session) -> dict:
        """Whole-session risk score plus a windowed timeline, for a finished (or in-progress)
        session being reviewed after the fact - unlike compute_risk, which only scores a trailing
        WINDOW_SECONDS from *now* and is meaningful only for a session that's still live. Used by
        the student-facing results/dashboard views instead of them re-deriving this client-side
        (see the frontend for why that used to be duplicated in JS - not viable once part of the
        scoring is a fitted model rather than a fixed weight dict)."""

        violations = (
            db.query(Violation)
            .filter(Violation.exam_session_id == session.id)
            .order_by(Violation.created_at)
            .all()
        )

        risk_score = _score(violations)

        start_time = session.started_at
        end_time = session.submitted_at or datetime.now(timezone.utc)
        if violations:
            start_time = min(start_time, violations[0].created_at)
            end_time = max(end_time, violations[-1].created_at)

        timeline = []
        for i in range(TIMELINE_POINTS):
            fraction = i / (TIMELINE_POINTS - 1) if TIMELINE_POINTS > 1 else 0.0
            t = start_time + (end_time - start_time) * fraction
            window_start = t - timedelta(seconds=WINDOW_SECONDS)
            windowed = [v for v in violations if window_start <= v.created_at <= t]
            timeline.append({"time": t, "risk": _score(windowed)})

        return {"risk_score": risk_score, "timeline": timeline}

    @staticmethod
    def get_live_sessions(db: Session, school_id: int):

        # Previously queried every IN_PROGRESS session in the entire deployment with zero
        # scoping - any instructor could watch every other instructor's (and, once multi-tenant,
        # every other school's) live exam sessions.
        sessions = (
            db.query(ExamSession)
            .join(Exam, ExamSession.exam_id == Exam.id)
            .join(Subject, Exam.subject_id == Subject.id)
            .join(Course, Subject.course_id == Course.id)
            .filter(ExamSession.status == "IN_PROGRESS", Course.school_id == school_id)
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
                "student_name": (s.student.student_name if s.student else None) or f"#{s.student_id}",
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
                "student_name": (
                    (sessions_by_id[v.exam_session_id].student.student_name
                     if sessions_by_id[v.exam_session_id].student else None)
                    or f"#{sessions_by_id[v.exam_session_id].student_id}"
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
