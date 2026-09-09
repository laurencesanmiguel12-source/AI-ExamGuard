"""One violation per episode, not one per poll.

PHONE_DETECTED and MULTIPLE_PEOPLE were the only two detectors without fire-once-per-episode
tracking, so they re-logged every poll for as long as the condition held. Observed live on
2026-09-09: 6 MULTIPLE_PEOPLE rows in 50 seconds and 4 PHONE_DETECTED rows in 35 from single
continuous episodes.

That matters beyond log noise - risk is scored from violation counts, so one continuous episode
scored differently depending only on how many times it happened to be polled.
"""
from app.services.violation_episodes import (
    EPISODE_CLEAR_TOLERANCE,
    begin_episode,
    discard_session,
    end_episode,
)


def clear_fully(session, event):
    """A real episode only ends after EPISODE_CLEAR_TOLERANCE consecutive negative polls."""
    for _ in range(EPISODE_CLEAR_TOLERANCE):
        end_episode(session, event)

SESSION = 4242


def setup_function():
    discard_session(SESSION)


def teardown_function():
    discard_session(SESSION)


def test_one_log_for_a_sustained_episode():
    assert begin_episode(SESSION, "PHONE_DETECTED") is True, "first poll must log"
    for _ in range(20):
        assert begin_episode(SESSION, "PHONE_DETECTED") is False, "must not re-log while held"


def test_the_condition_clearing_re_arms_it():
    begin_episode(SESSION, "PHONE_DETECTED")
    clear_fully(SESSION, "PHONE_DETECTED")

    assert begin_episode(SESSION, "PHONE_DETECTED") is True, "a new episode is a new violation"


def test_a_real_gap_still_counts_as_two_episodes():
    # Put the phone down and pick it up again: genuinely two events, and the instructor should
    # see both.
    assert begin_episode(SESSION, "PHONE_DETECTED") is True
    clear_fully(SESSION, "PHONE_DETECTED")
    assert begin_episode(SESSION, "PHONE_DETECTED") is True


def test_a_single_flickering_poll_does_not_re_fire():
    """The bug seen live: a held phone whose confidence oscillates across the threshold logged
    six violations in two minutes, because one negative poll re-armed the event."""
    assert begin_episode(SESSION, "PHONE_DETECTED") is True

    for _ in range(10):
        end_episode(SESSION, "PHONE_DETECTED")          # one dip below threshold
        assert begin_episode(SESSION, "PHONE_DETECTED") is False, "a flicker is not a new episode"


def test_a_positive_poll_resets_the_clear_streak():
    """Otherwise alternating detect/miss would creep up on the tolerance and eventually re-fire
    in the middle of one continuous episode."""
    assert begin_episode(SESSION, "PHONE_DETECTED") is True
    for _ in range(20):
        end_episode(SESSION, "PHONE_DETECTED")
        assert begin_episode(SESSION, "PHONE_DETECTED") is False


def test_identity_mismatch_uses_the_same_tracker():
    # Logged from face_service, not object_detection_service - the whole reason this lives in its
    # own module. Three IDENTITY_MISMATCH rows fired for one seated student before this.
    assert begin_episode(SESSION, "IDENTITY_MISMATCH") is True
    assert begin_episode(SESSION, "IDENTITY_MISMATCH") is False


def test_event_types_are_tracked_independently():
    # A phone episode must not suppress a separate multiple-people episode.
    assert begin_episode(SESSION, "PHONE_DETECTED") is True
    assert begin_episode(SESSION, "MULTIPLE_PEOPLE") is True
    assert begin_episode(SESSION, "PHONE_DETECTED") is False
    assert begin_episode(SESSION, "MULTIPLE_PEOPLE") is False

    clear_fully(SESSION, "PHONE_DETECTED")
    assert begin_episode(SESSION, "PHONE_DETECTED") is True
    assert begin_episode(SESSION, "MULTIPLE_PEOPLE") is False, "clearing one must not clear both"


def test_sessions_do_not_share_episode_state():
    other = SESSION + 1
    try:
        assert begin_episode(SESSION, "MULTIPLE_PEOPLE") is True
        # A different student in their own session must still get their own first violation.
        assert begin_episode(other, "MULTIPLE_PEOPLE") is True
    finally:
        discard_session(other)


def test_ending_an_episode_that_never_started_is_harmless():
    # Every poll with no phone calls this, including the very first one of a session.
    clear_fully(SESSION, "PHONE_DETECTED")
    assert begin_episode(SESSION, "PHONE_DETECTED") is True


def test_discard_session_clears_the_state():
    begin_episode(SESSION, "PHONE_DETECTED")
    discard_session(SESSION)

    # Otherwise the dict grows by one entry per exam session ever taken, for the life of the
    # process - the same leak discard_session already exists to prevent for the other two dicts.
    assert begin_episode(SESSION, "PHONE_DETECTED") is True
