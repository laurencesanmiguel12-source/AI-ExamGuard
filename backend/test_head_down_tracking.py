from datetime import timedelta

from app.services.face_service import (
    _track_head_down,
    _is_head_down,
    HEAD_DOWN_PITCH_THRESHOLD_DEGREES,
    HEAD_DOWN_DURATION_THRESHOLD_SECONDS,
)

DOWN_POSE = {"pitch": HEAD_DOWN_PITCH_THRESHOLD_DEGREES - 5, "yaw": 0, "roll": 0}
UP_POSE = {"pitch": HEAD_DOWN_PITCH_THRESHOLD_DEGREES + 5, "yaw": 0, "roll": 0}


class FakeSession:
    head_down_since = None
    head_down_consecutive_count = 0
    head_down_violation_logged = False


print("========== _is_head_down threshold sign ==========")
assert _is_head_down(DOWN_POSE) is True
assert _is_head_down(UP_POSE) is False
assert _is_head_down(None) is False
print("OK")

print("\n========== streak build-up ==========")
session = FakeSession()
duration, should_log = _track_head_down(session, None)
assert duration == 0.0 and should_log is False
assert session.head_down_since is None and session.head_down_consecutive_count == 0
print(f"not down: duration={duration}, should_log={should_log}, count={session.head_down_consecutive_count}")

duration, should_log = _track_head_down(session, DOWN_POSE)
assert session.head_down_since is not None and session.head_down_consecutive_count == 1
assert should_log is False, "must not fire before crossing the duration threshold"
print(f"1st down poll: duration={duration:.3f}, should_log={should_log}, count={session.head_down_consecutive_count}")

first_since = session.head_down_since
duration, should_log = _track_head_down(session, DOWN_POSE)
assert session.head_down_since == first_since, "since timestamp must not reset while streak continues"
assert session.head_down_consecutive_count == 2
assert should_log is False
print(f"2nd down poll: duration={duration:.3f}, should_log={should_log}, count={session.head_down_consecutive_count}")

print("\n========== streak reset on recovery ==========")
duration, should_log = _track_head_down(session, UP_POSE)
assert duration == 0.0 and should_log is False
assert session.head_down_since is None and session.head_down_consecutive_count == 0
assert session.head_down_violation_logged is False
print(f"recovered: duration={duration}, should_log={should_log}, count={session.head_down_consecutive_count}")

print("\n========== violation fires exactly once per streak ==========")
session = FakeSession()
_track_head_down(session, DOWN_POSE)
# backdate the streak start to simulate elapsed polling time without a real sleep
session.head_down_since -= timedelta(seconds=HEAD_DOWN_DURATION_THRESHOLD_SECONDS + 1)

duration, should_log = _track_head_down(session, DOWN_POSE)
assert duration >= HEAD_DOWN_DURATION_THRESHOLD_SECONDS
assert should_log is True, "must fire on the poll where the threshold is first crossed"
assert session.head_down_violation_logged is True
print(f"crossing poll: duration={duration:.1f}s (threshold={HEAD_DOWN_DURATION_THRESHOLD_SECONDS}s), should_log={should_log}")

duration, should_log = _track_head_down(session, DOWN_POSE)
assert should_log is False, "must not re-fire on subsequent polls while still in the same streak"
print(f"next poll, still down: duration={duration:.1f}s, should_log={should_log}")

duration, should_log = _track_head_down(session, UP_POSE)
assert should_log is False and session.head_down_violation_logged is False
print(f"recovered: violation_logged reset to {session.head_down_violation_logged}")

print("\n========== a second streak can fire again ==========")
_track_head_down(session, DOWN_POSE)
session.head_down_since -= timedelta(seconds=HEAD_DOWN_DURATION_THRESHOLD_SECONDS + 1)
duration, should_log = _track_head_down(session, DOWN_POSE)
assert should_log is True, "a new streak must be able to trigger its own violation"
print(f"second streak crossing: duration={duration:.1f}s, should_log={should_log}")

print("\nAll checks passed.")
