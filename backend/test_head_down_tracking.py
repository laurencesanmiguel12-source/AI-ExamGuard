from datetime import timedelta

from app.services.face_service import (
    _track_head_down,
    _is_head_down,
    HEAD_DOWN_PITCH_THRESHOLD_DEGREES,
    HEAD_DOWN_DURATION_THRESHOLD_SECONDS,
    HEAD_DOWN_MISS_TOLERANCE,
)

DOWN_POSE = {"pitch": HEAD_DOWN_PITCH_THRESHOLD_DEGREES - 5, "yaw": 0, "roll": 0}
UP_POSE = {"pitch": HEAD_DOWN_PITCH_THRESHOLD_DEGREES + 5, "yaw": 0, "roll": 0}


class FakeSession:
    head_down_since = None
    head_down_consecutive_count = 0
    head_down_miss_streak = 0
    head_down_violation_logged = False


print("========== _is_head_down threshold sign ==========")
assert _is_head_down(DOWN_POSE) is True
assert _is_head_down(UP_POSE) is False
assert _is_head_down(None) is False
print("OK")

print(f"\n(HEAD_DOWN_MISS_TOLERANCE = {HEAD_DOWN_MISS_TOLERANCE} - test below assumes this is 1;"
      " update the tolerance-specific assertions if that constant ever changes.)")
assert HEAD_DOWN_MISS_TOLERANCE == 1

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

print("\n========== a single miss is forgiven (HEAD_DOWN_MISS_TOLERANCE=1) ==========")
# Regression test for the 2026-07-31 system-level simulation finding: resetting on ANY single
# miss made the feature never fire across all 4 real timestamped test sequences, even during
# obvious 28-43s sustained phone-use episodes, because pitch is noisy enough that isolated polls
# routinely read just above threshold mid-streak.
duration, should_log = _track_head_down(session, UP_POSE)
assert should_log is False
assert session.head_down_since == first_since, "a single miss must not reset the streak's start time"
assert session.head_down_miss_streak == 1
print(f"1 miss (forgiven): since unchanged={session.head_down_since == first_since}, "
      f"miss_streak={session.head_down_miss_streak}, duration={duration:.3f}")

# Recovering (a down poll) clears the miss counter without losing accumulated progress.
duration, should_log = _track_head_down(session, DOWN_POSE)
assert session.head_down_since == first_since
assert session.head_down_miss_streak == 0
assert session.head_down_consecutive_count == 3, "a forgiven miss must not itself count as progress"
print(f"recovered after 1 miss: since unchanged, miss_streak reset to 0, count={session.head_down_consecutive_count}")

print("\n========== streak resets only after exceeding tolerance ==========")
duration, should_log = _track_head_down(session, UP_POSE)  # miss 1
assert session.head_down_since == first_since
duration, should_log = _track_head_down(session, UP_POSE)  # miss 2 - exceeds tolerance of 1
assert should_log is False
assert session.head_down_since is None and session.head_down_consecutive_count == 0
assert session.head_down_violation_logged is False and session.head_down_miss_streak == 0
print(f"2 consecutive misses: streak actually reset (since={session.head_down_since}, "
      f"count={session.head_down_consecutive_count})")

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

# Exceed tolerance to force a real reset (a single miss would now be forgiven, not reset).
_track_head_down(session, UP_POSE)
duration, should_log = _track_head_down(session, UP_POSE)
assert should_log is False and session.head_down_violation_logged is False
print(f"recovered after exceeding tolerance: violation_logged reset to {session.head_down_violation_logged}")

print("\n========== a second streak can fire again ==========")
_track_head_down(session, DOWN_POSE)
session.head_down_since -= timedelta(seconds=HEAD_DOWN_DURATION_THRESHOLD_SECONDS + 1)
duration, should_log = _track_head_down(session, DOWN_POSE)
assert should_log is True, "a new streak must be able to trigger its own violation"
print(f"second streak crossing: duration={duration:.1f}s, should_log={should_log}")

print("\n========== pose-model fallback: head present but no numeric pose ==========")
# Regression test for the 2026-07-31 live smoke-test finding: a real head-down tilt made YuNet
# lose facial landmarks entirely (pose=None), so the streak never built up even though a head
# was clearly still in frame. _head_present_via_fallback lets a poll continue the streak in that
# exact situation instead of resetting it.
assert _is_head_down(None, head_present_via_fallback=True) is True
assert _is_head_down(None, head_present_via_fallback=False) is False

session = FakeSession()
duration, should_log = _track_head_down(session, None, head_present_via_fallback=True)
assert session.head_down_since is not None and session.head_down_consecutive_count == 1
assert should_log is False
print(f"1st fallback-only poll (no numeric pose): duration={duration:.3f}, count={session.head_down_consecutive_count}")

first_since = session.head_down_since
duration, should_log = _track_head_down(session, None, head_present_via_fallback=True)
assert session.head_down_since == first_since, "streak must continue, not restart, across fallback-only polls"
assert session.head_down_consecutive_count == 2
print(f"2nd fallback-only poll: duration={duration:.3f}, count={session.head_down_consecutive_count}")

# A real FACE_LOST (no head at all, fallback also empty) counts as a miss like any other - one
# is forgiven, two consecutive exceed tolerance and reset the streak.
duration, should_log = _track_head_down(session, None, head_present_via_fallback=False)
assert session.head_down_since == first_since, "a single genuine no-head poll must still be forgiven"
duration, should_log = _track_head_down(session, None, head_present_via_fallback=False)
assert duration == 0.0 and should_log is False
assert session.head_down_since is None and session.head_down_consecutive_count == 0
print(f"2 consecutive genuine no-head polls: duration={duration}, count={session.head_down_consecutive_count} (streak reset)")

# A streak can cross the duration threshold via fallback-only polls alone.
session = FakeSession()
_track_head_down(session, None, head_present_via_fallback=True)
session.head_down_since -= timedelta(seconds=HEAD_DOWN_DURATION_THRESHOLD_SECONDS + 1)
duration, should_log = _track_head_down(session, None, head_present_via_fallback=True)
assert should_log is True, "a fallback-only streak must still be able to cross the threshold and fire"
print(f"fallback-only streak crossing: duration={duration:.1f}s, should_log={should_log}")

print("\nAll checks passed.")
