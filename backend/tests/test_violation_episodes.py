"""One violation per episode, not one per poll.

PHONE_DETECTED and MULTIPLE_PEOPLE were the only two detectors without fire-once-per-episode
tracking, so they re-logged every poll for as long as the condition held. Observed live on
2026-09-09: 6 MULTIPLE_PEOPLE rows in 50 seconds and 4 PHONE_DETECTED rows in 35 from single
continuous episodes.

That matters beyond log noise - risk is scored from violation counts, so one continuous episode
scored differently depending only on how many times it happened to be polled.
"""
from app.services.object_detection_service import (
    _begin_episode,
    _end_episode,
    discard_session,
)

SESSION = 4242


def setup_function():
    discard_session(SESSION)


def teardown_function():
    discard_session(SESSION)


def test_one_log_for_a_sustained_episode():
    assert _begin_episode(SESSION, "PHONE_DETECTED") is True, "first poll must log"
    for _ in range(20):
        assert _begin_episode(SESSION, "PHONE_DETECTED") is False, "must not re-log while held"


def test_the_condition_clearing_re_arms_it():
    _begin_episode(SESSION, "PHONE_DETECTED")
    _end_episode(SESSION, "PHONE_DETECTED")

    assert _begin_episode(SESSION, "PHONE_DETECTED") is True, "a new episode is a new violation"


def test_a_brief_gap_still_counts_as_two_episodes():
    # Put the phone down and pick it up again: genuinely two events, and the instructor should
    # see both.
    assert _begin_episode(SESSION, "PHONE_DETECTED") is True
    _end_episode(SESSION, "PHONE_DETECTED")
    assert _begin_episode(SESSION, "PHONE_DETECTED") is True


def test_event_types_are_tracked_independently():
    # A phone episode must not suppress a separate multiple-people episode.
    assert _begin_episode(SESSION, "PHONE_DETECTED") is True
    assert _begin_episode(SESSION, "MULTIPLE_PEOPLE") is True
    assert _begin_episode(SESSION, "PHONE_DETECTED") is False
    assert _begin_episode(SESSION, "MULTIPLE_PEOPLE") is False

    _end_episode(SESSION, "PHONE_DETECTED")
    assert _begin_episode(SESSION, "PHONE_DETECTED") is True
    assert _begin_episode(SESSION, "MULTIPLE_PEOPLE") is False, "clearing one must not clear both"


def test_sessions_do_not_share_episode_state():
    other = SESSION + 1
    try:
        assert _begin_episode(SESSION, "MULTIPLE_PEOPLE") is True
        # A different student in their own session must still get their own first violation.
        assert _begin_episode(other, "MULTIPLE_PEOPLE") is True
    finally:
        discard_session(other)


def test_ending_an_episode_that_never_started_is_harmless():
    # Every poll with no phone calls this, including the very first one of a session.
    _end_episode(SESSION, "PHONE_DETECTED")
    assert _begin_episode(SESSION, "PHONE_DETECTED") is True


def test_discard_session_clears_the_state():
    _begin_episode(SESSION, "PHONE_DETECTED")
    discard_session(SESSION)

    # Otherwise the dict grows by one entry per exam session ever taken, for the life of the
    # process - the same leak discard_session already exists to prevent for the other two dicts.
    assert _begin_episode(SESSION, "PHONE_DETECTED") is True
