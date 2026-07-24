from app.schemas.violation import ViolationCreate, ViolationResponse, RecentViolation
from app.services.risk_service import WEIGHTS, _score
from datetime import datetime, timezone

print("========== VIOLATION CREATE (with detail) ==========")

create = ViolationCreate(event_type="AI_TOOL_DETECTED", detail="chatgpt.com")
print(create)

print("\n========== VIOLATION CREATE (no detail, backward compatible) ==========")

create_no_detail = ViolationCreate(event_type="TAB_SWITCH")
print(create_no_detail)
assert create_no_detail.detail is None

print("\n========== VIOLATION RESPONSE ==========")

response = ViolationResponse(
    id=1,
    exam_session_id=1,
    event_type="AI_TOOL_DETECTED",
    detail="chatgpt.com",
    created_at=datetime.now(timezone.utc),
)
print(response)

print("\n========== RECENT VIOLATION ==========")

recent = RecentViolation(
    session_id=1,
    student_number="2026-0003",
    exam_id=1,
    event_type="SEARCH_ENGINE_DETECTED",
    detail="www.google.com",
    created_at=datetime.now(timezone.utc),
)
print(recent)

print("\n========== RISK WEIGHTS ==========")

assert "AI_TOOL_DETECTED" in WEIGHTS and WEIGHTS["AI_TOOL_DETECTED"] == 40
assert "SEARCH_ENGINE_DETECTED" in WEIGHTS and WEIGHTS["SEARCH_ENGINE_DETECTED"] == 35
print(f"AI_TOOL_DETECTED weight: {WEIGHTS['AI_TOOL_DETECTED']}")
print(f"SEARCH_ENGINE_DETECTED weight: {WEIGHTS['SEARCH_ENGINE_DETECTED']}")


class FakeViolation:
    def __init__(self, event_type):
        self.event_type = event_type


score_one_ai_tool = _score([FakeViolation("AI_TOOL_DETECTED")])
score_capped = _score([FakeViolation("AI_TOOL_DETECTED"), FakeViolation("AI_TOOL_DETECTED"), FakeViolation("AI_TOOL_DETECTED")])
print(f"\nScore for 1x AI_TOOL_DETECTED: {score_one_ai_tool} (expect 40)")
print(f"Score for 3x AI_TOOL_DETECTED (capped): {score_capped} (expect 100)")
assert score_one_ai_tool == 40.0
assert score_capped == 100.0

print("\nAll checks passed.")
