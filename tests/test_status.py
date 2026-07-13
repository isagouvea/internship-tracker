from datetime import date, timedelta

from internship_tracker.status import status_after_verification


def test_one_failure_does_not_close():
    assert status_after_verification("open", seen=False, consecutive_failures=0)[0] == "may_have_closed"


def test_seen_event_becomes_open_on_later_verification():
    assert status_after_verification("new", seen=True) == ("open", 0)


def test_two_failures_close():
    assert status_after_verification("may_have_closed", seen=False, consecutive_failures=1) == ("closed", 2)


def test_explicit_closure_and_past_deadline_close():
    assert status_after_verification("open", explicitly_closed=True)[0] == "closed"
    assert status_after_verification("open", deadline=date.today() - timedelta(days=1))[0] == "closed"
