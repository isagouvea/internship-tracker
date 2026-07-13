from datetime import datetime, timezone

import pytest

from internship_tracker.database import session_factory
from internship_tracker.models import Company, Posting, SearchRun


@pytest.fixture
def session(tmp_path):
    factory = session_factory(tmp_path / "test.db")
    with factory() as value:
        yield value


@pytest.fixture
def company(session):
    value = Company(name="Test Company", careers_url="https://careers.example.com", ats_provider="generic")
    session.add(value); session.commit()
    return value


@pytest.fixture
def run(session):
    value = SearchRun(mode="test", successful=True, completed_at=datetime.now(timezone.utc))
    session.add(value); session.commit()
    return value


@pytest.fixture
def profile():
    return {
        "academic_status": "Undergraduate community-college student preparing to transfer",
        "intended_major": "Marketing", "gpa": 4.0, "current_class_standing": "unknown",
        "expected_bachelors_graduation": "Spring 2029", "work_authorization": "US citizen",
    }

