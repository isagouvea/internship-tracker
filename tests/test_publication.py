import csv
import json

from internship_tracker.adapters.base import DiscoveredJob
from internship_tracker.publication import PUBLIC_FIELDS, collect_public_jobs, generate_site, privacy_check, sanitize_posting, write_exports
from internship_tracker.search import upsert_job


def seeded(session, company, run, profile):
    job = DiscoveredJob(company=company.name, title="Summer 2027 Brand Marketing Intern", official_url="https://careers.example.com/apply/10",
                        requisition_id="10", location="Austin, TX", work_arrangement="Hybrid", internship_term="Summer 2027",
                        summary="Support a brand marketing team.", responsibilities="Research and campaign reporting.",
                        required_qualifications="Currently enrolled undergraduate authorized in the United States",
                        preferred_qualifications="Prior analytics exposure", education_requirement="Undergraduate enrollment",
                        compensation="$22/hour")
    posting, _ = upsert_job(session, company, job, run, profile); session.commit()
    return posting


def test_public_data_is_allowlisted(session, company, run, profile):
    posting = seeded(session, company, run, profile)
    data = sanitize_posting(posting)
    assert set(data) == set(PUBLIC_FIELDS)
    assert "gpa" not in data and "work_experience" not in data


def test_static_site_csv_and_json_generation(session, company, run, profile, tmp_path):
    seeded(session, company, run, profile)
    docs = tmp_path / "docs"
    state_path = tmp_path / "state" / "public_state.json"
    jobs, summary = generate_site(session, docs, state_path=state_path)
    assert (docs / "index.html").exists() and (docs / "404.html").exists()
    assert (docs / "assets" / "app.js").exists() and (docs / "data" / "summary.json").exists()
    assert json.loads((docs / "data" / "jobs.json").read_text())[0]["company"] == company.name
    with (docs / "downloads" / "open-internships.csv").open() as handle:
        assert next(csv.DictReader(handle))["title"].endswith("Intern")
    exports = tmp_path / "exports"; write_exports(jobs, exports)
    assert json.loads((exports / "internships.json").read_text())[0]["eligibility"] == "Likely eligible"
    assert list(csv.DictReader((exports / "internships.csv").open()))
    assert summary["open"] == 1
    public_state = json.loads(state_path.read_text())
    assert all("eligibility" not in item and "gpa" not in item for item in public_state["jobs"])


def test_privacy_check_detects_secret_and_private_profile_field(tmp_path):
    docs = tmp_path / "docs"; docs.mkdir()
    (docs / "bad.txt").write_text("student_id: 123 and api_key=abcdefghijklmnop")
    problems = privacy_check(docs)
    assert any("private profile field" in x for x in problems)
    assert any("API secret" in x for x in problems)


def test_clean_generated_site_passes_privacy(session, company, run, profile, tmp_path):
    seeded(session, company, run, profile)
    docs = tmp_path / "docs"; generate_site(session, docs, state_path=tmp_path / "state.json")
    assert privacy_check(docs) == []
