"""The person-count model runs every Nth poll instead of every one.

The base yolov8s model is 58% of a frame's inference on the deploy host and its entire output is
a person count. Two ways of making that count cheaper were measured on real evidence frames and
both changed the >1 decision - yolov8n-pose disagreed in 2 of 29 frames, and the same weights at
imgsz=512 lost a genuine second person in 2 of 15. So the count is taken less often instead,
which is what its timescale calls for: a phone is glanced at for a second, a second person in the
room is there for minutes.

The rule that keeps it honest is that a frame the model never looked at may not decide anything.
"""
import pytest

from app.core.config import settings
from app.services import object_detection_service as ods


@pytest.fixture(autouse=True)
def _clean_state():
    ods._person_count_state.clear()
    yield
    ods._person_count_state.clear()


@pytest.fixture
def every_third(monkeypatch):
    monkeypatch.setattr(settings, "PERSON_COUNT_EVERY_N_POLLS", 3)


def test_the_first_poll_of_a_session_always_counts(every_third):
    """A student's very first frame must be examined - starting a session one person short of the
    truth and waiting two polls to notice is the wrong direction to be wrong in."""
    assert ods._should_count_people(1) is True


def test_it_then_counts_every_nth_poll(every_third):
    decisions = [ods._should_count_people(1) for _ in range(9)]

    assert decisions == [True, False, False, True, False, False, True, False, False]


def test_each_session_is_counted_on_its_own_schedule(every_third):
    """Per session, not global. A global counter would sample one student three polls running and
    the next not at all, which is the one distribution that leaves somebody unwatched."""
    a = [ods._should_count_people(1) for _ in range(3)]
    b = [ods._should_count_people(2) for _ in range(3)]

    assert a == [True, False, False]
    assert b == [True, False, False]


def test_a_skipped_poll_reports_the_last_measured_count(every_third):
    ods._should_count_people(1)
    ods._remember_person_count(1, 2)

    ods._should_count_people(1)  # skipped poll

    assert ods._last_person_count(1) == 2


def test_setting_it_to_one_restores_per_frame_counting(monkeypatch):
    monkeypatch.setattr(settings, "PERSON_COUNT_EVERY_N_POLLS", 1)

    assert [ods._should_count_people(1) for _ in range(4)] == [True, True, True, True]


def test_a_nonsense_setting_does_not_disable_counting(monkeypatch):
    """0 or a negative would mean "never count anybody", which is a silent loss of a detector."""
    monkeypatch.setattr(settings, "PERSON_COUNT_EVERY_N_POLLS", 0)

    assert [ods._should_count_people(1) for _ in range(3)] == [True, True, True]


def test_finishing_a_session_drops_its_counter(every_third):
    """Same eviction the episode state gets - otherwise this grows by one entry per exam session
    ever taken, which is the unbounded-dict shape a previous audit already found once."""
    ods._should_count_people(7)
    ods._remember_person_count(7, 3)

    ods.ObjectDetectionService.discard_session(7)

    assert 7 not in ods._person_count_state


def test_the_response_says_whether_the_count_was_measured_or_carried(every_third):
    """The client renders a live person count. Without this it cannot tell a fresh reading from a
    repeated one, and would show a stale number as though it were current."""
    import inspect

    source = inspect.getsource(ods.ObjectDetectionService.check)
    assert '"person_count_fresh": counted_people' in source
    # the early-return paths carry the field too, rather than omitting it
    assert source.count("person_count_fresh") >= 3


def test_only_a_counted_frame_may_open_or_close_an_episode():
    """The rule the whole change rests on. A stale positive would keep resetting the clear streak
    on frames nobody counted; a stale negative would advance it toward closing an episode that is
    still running. Either way the decision comes from evidence that was never examined."""
    import inspect

    source = inspect.getsource(ods.ObjectDetectionService.check)
    multiple = source[source.index("MULTIPLE_PEOPLE") - 400: source.index("MULTIPLE_PEOPLE")]
    assert "if counted_people:" in multiple
