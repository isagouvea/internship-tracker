from internship_tracker.adapters.base import DiscoveredJob
from internship_tracker.eligibility import assess


def job(**values):
    return DiscoveredJob(company="Example", title="Marketing Intern", official_url="https://example.com", **values)


def test_likely_eligible(profile):
    result = assess(job(required_qualifications="Currently enrolled undergraduate authorized in the United States", required_major="Marketing or related", minimum_gpa=3.0), profile)
    assert result.classification == "Likely eligible" and result.confidence > 70


def test_four_year_requirement_is_direct_conflict(profile):
    result = assess(job(education_requirement="Must be enrolled at a four-year university"), profile)
    assert result.classification == "Likely not eligible"
    assert "four-year" in result.explanation


def test_unknown_requirement_is_unable_to_determine(profile):
    result = assess(job(), profile)
    assert result.classification == "Unable to determine"


def test_preferred_is_not_mandatory(profile):
    result = assess(job(required_qualifications="Currently enrolled undergraduate", preferred_qualifications="MBA preferred"), profile)
    assert result.classification == "Likely eligible"
    assert not result.conflicts

