from sqlalchemy import inspect, select

from internship_tracker.adapters.base import DiscoveredJob
from internship_tracker.database import initialize_database
from internship_tracker.models import Posting
from internship_tracker.search import upsert_job


def test_database_initialization_creates_normalized_tables(tmp_path):
    engine = initialize_database(tmp_path / "tracker.db")
    names = set(inspect(engine).get_table_names())
    assert {"companies", "postings", "source_urls", "requirements", "eligibility_assessments",
            "search_runs", "company_checks", "change_history"} <= names


def test_database_update_and_deduplication(session, company, run, profile):
    first = DiscoveredJob(company=company.name, title="Summer 2027 Marketing Intern", official_url="https://careers.example.com/jobs/1",
                          requisition_id="REQ-1", location="Dallas, TX", internship_term="Summer 2027",
                          required_qualifications="Currently enrolled undergraduate; authorized in the United States")
    posting, action = upsert_job(session, company, first, run, profile); session.commit()
    assert action == "new"
    assert posting.requirements and posting.requirements[0].mandatory
    duplicate = DiscoveredJob(**{**first.__dict__, "official_url": "https://careers.example.com/jobs/1?source=feed",
                                 "source_urls": ["https://feed.example.com/req-1"]})
    same, action = upsert_job(session, company, duplicate, run, profile); session.commit()
    assert same.id == posting.id and action == "duplicate"
    assert len(session.scalars(select(Posting)).all()) == 1
    # Tracking-query variants collapse to the canonical official source; the feed remains separate.
    assert len(same.sources) == 2


def test_changed_fingerprint_records_history(session, company, run, profile):
    job = DiscoveredJob(company=company.name, title="Summer 2027 Marketing Intern", official_url="https://careers.example.com/2",
                        requisition_id="2", summary="Marketing internship Summer 2027", required_qualifications="Currently enrolled")
    posting, _ = upsert_job(session, company, job, run, profile); session.commit()
    job.compensation = "$20/hour"
    posting, action = upsert_job(session, company, job, run, profile); session.commit()
    assert action == "changed" and posting.current_status == "changed"
    assert any(c.change_type == "content_changed" for c in posting.changes)
