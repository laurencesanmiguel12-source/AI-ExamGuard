"""One violation per episode, shared by every detector that has a sustained on/off condition.

**Why this exists.** A detector that logs on every poll where its condition holds turns one
continuous event into as many violations as the machine happened to sample. Observed live on
2026-09-09: six PHONE_DETECTED and six MULTIPLE_PEOPLE rows in under a minute each, and three
IDENTITY_MISMATCH rows for one continuously seated student. Beyond unreadable timelines, risk is
scored from violation COUNTS - so the same behaviour scored differently on a fast machine than a
slow one, and multiple_people carries the largest coefficient in the fitted model.

**Why clearing needs tolerance.** The first version closed an episode on a single negative poll,
and a continuously held phone still logged six times: the detector's confidence oscillates across
its threshold frame to frame (this deployment recorded 0.230 and 0.246 between firings at a 0.25
threshold), so one dip re-armed the event and the next frame fired it again. This is the same
shape of bug HEAD_DOWN_MISS_TOLERANCE was added for, in the opposite direction - there,
reset-on-any-miss meant the feature never fired; here it meant it never stopped.

Lives in its own module rather than inside either detector because face_service and
object_detection_service both need it and already reference each other.

Same in-memory-per-session tradeoff as the other detector state in this codebase: lost on
restart, single-process only, and evicted by discard_session() so it cannot grow by one entry per
exam session ever taken.
"""

# Consecutive negative polls required to end an episode. 2 covers every single-poll dip seen live
# while still treating a genuinely ended episode (two clean polls - roughly 10-40s at real poll
# spacing) as over.
EPISODE_CLEAR_TOLERANCE = 2

# session_id -> {event_type: consecutive negative polls since it fired}. Presence of the
# event_type key means that episode is currently open.
_episode_open: dict[int, dict[str, int]] = {}


def begin_episode(session_id: int, event_type: str) -> bool:
    """True only on the transition INTO an episode - i.e. the one poll that should log."""
    open_for_session = _episode_open.setdefault(session_id, {})
    if event_type in open_for_session:
        # Still the same episode. A positive poll cancels any part-accumulated clear streak, so a
        # flickering signal can never creep up on the tolerance and re-arm mid-episode.
        open_for_session[event_type] = 0
        return False
    open_for_session[event_type] = 0
    return True


def end_episode(session_id: int, event_type: str) -> None:
    """Counts one negative poll, re-arming only after EPISODE_CLEAR_TOLERANCE consecutive ones."""
    open_for_session = _episode_open.get(session_id)
    if not open_for_session or event_type not in open_for_session:
        return
    open_for_session[event_type] += 1
    if open_for_session[event_type] >= EPISODE_CLEAR_TOLERANCE:
        del open_for_session[event_type]


def discard_session(session_id: int) -> None:
    """Drops a finished session's episode state. Safe if the session never opened one."""
    _episode_open.pop(session_id, None)
