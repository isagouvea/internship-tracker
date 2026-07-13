from __future__ import annotations

import csv
import hashlib
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from .constants import DOCS_DIR, ROOT
from .models import EligibilityAssessment, Posting, SearchRun

PUBLIC_FIELDS = (
    "id", "company", "title", "category", "internship_term", "location", "state",
    "work_arrangement", "official_url", "summary", "responsibilities", "required_qualifications",
    "preferred_qualifications", "education_requirement", "required_major", "required_class_standing",
    "graduation_date_range", "minimum_gpa", "work_authorization_requirement", "sponsorship_information",
    "compensation", "posting_date", "application_deadline", "first_found", "last_confirmed",
    "current_status", "eligibility", "eligibility_confidence", "eligibility_explanation",
    "missing_candidate_information", "source_urls", "change_history", "new_since_last_search",
    "deadline_approaching", "fingerprint",
)


def _iso(value):
    return value.isoformat() if isinstance(value, (date, datetime)) else value


def sanitize_posting(posting: Posting, today: date | None = None) -> dict:
    today = today or date.today()
    assessment = max(posting.assessments, key=lambda x: x.id or 0) if posting.assessments else None
    deadline_approaching = bool(posting.application_deadline and today <= posting.application_deadline <= date.fromordinal(today.toordinal() + 14))
    data = {
        "id": posting.id, "company": posting.company.name, "title": posting.exact_title,
        "category": posting.category, "internship_term": posting.internship_term,
        "location": posting.location, "state": posting.state, "work_arrangement": posting.work_arrangement,
        "official_url": posting.official_url, "summary": posting.description_summary,
        "responsibilities": posting.responsibilities, "required_qualifications": posting.required_qualifications,
        "preferred_qualifications": posting.preferred_qualifications,
        "education_requirement": posting.education_requirement, "required_major": posting.required_major,
        "required_class_standing": posting.required_class_standing, "graduation_date_range": posting.graduation_date_range,
        "minimum_gpa": posting.minimum_gpa, "work_authorization_requirement": posting.work_authorization_requirement,
        "sponsorship_information": posting.sponsorship_information, "compensation": posting.compensation,
        "posting_date": _iso(posting.posting_date), "application_deadline": _iso(posting.application_deadline),
        "first_found": _iso(posting.first_found), "last_confirmed": _iso(posting.last_confirmed),
        "current_status": posting.current_status,
        "eligibility": assessment.classification if assessment else "Unable to determine",
        "eligibility_confidence": assessment.confidence if assessment else 0,
        "eligibility_explanation": assessment.explanation if assessment else "No assessment is available.",
        "missing_candidate_information": json.loads(assessment.missing_candidate_details) if assessment else [],
        "source_urls": sorted({s.url for s in posting.sources}),
        "change_history": [{"date": _iso(c.changed_at), "type": c.change_type, "details": c.details} for c in sorted(posting.changes, key=lambda c: c.changed_at, reverse=True)],
        "new_since_last_search": posting.current_status == "new", "deadline_approaching": deadline_approaching,
        "fingerprint": posting.content_fingerprint,
    }
    assert set(data) == set(PUBLIC_FIELDS)
    return data


def collect_public_jobs(session: Session) -> list[dict]:
    postings = session.scalars(select(Posting).options(
        selectinload(Posting.company), selectinload(Posting.sources),
        selectinload(Posting.assessments), selectinload(Posting.changes)
    ).order_by(Posting.first_found.desc())).all()
    return [sanitize_posting(p) for p in postings]


def summary_for(session: Session, jobs: list[dict]) -> dict:
    latest = session.scalar(select(SearchRun).where(SearchRun.successful.is_(True)).order_by(SearchRun.completed_at.desc()))
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "latest_successful_update": _iso(latest.completed_at) if latest else None,
        "total": len(jobs), "new": sum(j["current_status"] == "new" for j in jobs),
        "open": sum(j["current_status"] in {"open", "new", "changed", "may_have_closed"} for j in jobs),
        "changed": sum(j["current_status"] == "changed" for j in jobs),
        "likely_eligible": sum(j["eligibility"] == "Likely eligible" for j in jobs),
        "possibly_eligible": sum(j["eligibility"] == "Possibly eligible" for j in jobs),
        "likely_not_eligible": sum(j["eligibility"] == "Likely not eligible" for j in jobs),
        "unable_to_determine": sum(j["eligibility"] == "Unable to determine" for j in jobs),
        "deadlines_within_14_days": sum(j["deadline_approaching"] for j in jobs),
    }


def write_exports(jobs: list[dict], exports_dir: Path) -> None:
    exports_dir.mkdir(parents=True, exist_ok=True)
    (exports_dir / "internships.json").write_text(json.dumps(jobs, indent=2, ensure_ascii=False), encoding="utf-8")
    columns = [x for x in PUBLIC_FIELDS if x not in {"source_urls", "change_history", "missing_candidate_information"}]
    with (exports_dir / "internships.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader(); writer.writerows(jobs)


def _write_csv(path: Path, jobs: list[dict]) -> None:
    columns = ["company", "title", "category", "internship_term", "location", "work_arrangement", "posting_date", "application_deadline", "compensation", "eligibility", "current_status", "official_url"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader(); writer.writerows(jobs)


def generate_site(session: Session, docs_dir: Path = DOCS_DIR, state_path: Path | None = None) -> tuple[list[dict], dict]:
    jobs = collect_public_jobs(session); summary = summary_for(session, jobs)
    for directory in (docs_dir / "assets", docs_dir / "data", docs_dir / "downloads"):
        directory.mkdir(parents=True, exist_ok=True)
    env = Environment(loader=FileSystemLoader(ROOT / "src" / "internship_tracker" / "templates"), autoescape=select_autoescape(["html"]))
    (docs_dir / "index.html").write_text(env.get_template("index.html").render(summary=summary), encoding="utf-8")
    (docs_dir / "404.html").write_text(env.get_template("404.html").render(), encoding="utf-8")
    (docs_dir / ".nojekyll").touch()
    for name in ("styles.css", "app.js"):
        source = ROOT / "src" / "internship_tracker" / "static" / name
        (docs_dir / "assets" / name).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    (docs_dir / "data" / "jobs.json").write_text(json.dumps(jobs, indent=2, ensure_ascii=False), encoding="utf-8")
    (docs_dir / "data" / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    open_jobs = [j for j in jobs if j["current_status"] != "closed"]
    _write_csv(docs_dir / "downloads" / "open-internships.csv", open_jobs)
    _write_csv(docs_dir / "downloads" / "eligible-internships.csv", [j for j in open_jobs if j["eligibility"] in {"Likely eligible", "Possibly eligible"}])
    state = [{"id": j["id"], "fingerprint": j["fingerprint"], "status": j["current_status"], "company": j["company"], "title": j["title"]} for j in jobs]
    state_path = state_path or ROOT / "state" / "public_state.json"; state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps({"jobs": state}, indent=2), encoding="utf-8")
    return jobs, summary


SECRET_PATTERNS = {
    "private profile field": re.compile(r'(?i)(candidate[_ -]?profile|student[_ -]?id|personal[_ -]?email|candidate[_ -]?address|candidate[_ -]?phone|linkedin_url|portfolio_url|complete[_ -]?resume|full[_ -]?resume|work[_ -]?history|private[_ -]?notes)'),
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "common API secret": re.compile(r'(?i)(api[_-]?key|client[_-]?secret|access[_-]?token)\s*[=:]\s*["\']?[A-Za-z0-9_\-]{12,}'),
    "AWS access key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "email address": re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I),
    "US phone number": re.compile(r"(?<!\d)(?:\+?1[-. ]?)?\(?\d{3}\)?[-. ]\d{3}[-. ]\d{4}(?!\d)"),
}


def privacy_check(docs_dir: Path = DOCS_DIR) -> list[str]:
    problems = []
    forbidden_suffixes = {".db", ".sqlite", ".sqlite3", ".env", ".pem", ".key"}
    sensitive_values: list[str] = []
    profile_path = ROOT / "config" / "candidate_profile.yaml"
    if profile_path.exists():
        try:
            import yaml
            profile = yaml.safe_load(profile_path.read_text(encoding="utf-8")) or {}
            for key in ("address", "phone", "personal_email", "email", "student_id", "linkedin_url", "portfolio_url"):
                value = profile.get(key)
                if isinstance(value, str) and value.lower() not in {"", "null", "unknown"}:
                    sensitive_values.append(value)
        except (ValueError, OSError):
            problems.append("Private candidate profile could not be parsed during privacy check")
    for path in docs_dir.rglob("*") if docs_dir.exists() else []:
        if not path.is_file(): continue
        if path.suffix.lower() in forbidden_suffixes:
            problems.append(f"Forbidden file type: {path}"); continue
        try: text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError: continue
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(text): problems.append(f"{label} detected in {path}")
        for value in sensitive_values:
            if value in text: problems.append(f"private candidate value detected in {path}")
    return problems


def write_report(session: Session, path: Path) -> None:
    jobs = collect_public_jobs(session); summary = summary_for(session, jobs)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Internship tracker report", "", f"Generated: {summary['generated_at']}", "",
             f"- Total historical postings: {summary['total']}", f"- Currently tracked as open: {summary['open']}",
             f"- New: {summary['new']}", f"- Changed: {summary['changed']}",
             f"- Deadlines within 14 days: {summary['deadlines_within_14_days']}", "", "## Open postings", ""]
    for job in jobs:
        if job["current_status"] != "closed": lines.append(f"- [{job['company']}: {job['title']}]({job['official_url']}) — {job['eligibility']}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
