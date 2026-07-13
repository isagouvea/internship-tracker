from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from difflib import SequenceMatcher
from urllib.parse import urlsplit, urlunsplit

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from .adapters import DiscoveredJob, adapter_for
from .config import CompanyConfig
from .constants import MARKETING_TERMS
from .eligibility import assess
from .models import (ChangeHistory, Company, CompanyCheck, EligibilityAssessment,
                     Posting, Requirement, SearchRun, SourceURL, utcnow)
from .status import status_after_verification


def normalize_url(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), "", ""))


def infer_fields(job: DiscoveredJob) -> DiscoveredJob:
    text = " ".join(filter(None, [job.title, job.summary, job.location])).lower()
    if "spring 2027" in text: job.internship_term = "Spring 2027"
    elif "summer 2027" in text: job.internship_term = "Summer 2027"
    elif "2027" in text: job.internship_term = "Unspecified 2027"
    if "remote" in text: job.work_arrangement = "Remote"
    elif "hybrid" in text: job.work_arrangement = "Hybrid"
    elif "on-site" in text or "onsite" in text: job.work_arrangement = "Onsite"
    if re.search(r"dallas|fort worth|plano|frisco|irving|richardson|arlington", text): job.state = job.state or "Texas"
    return job


def in_scope(job: DiscoveredJob) -> bool:
    text = " ".join(filter(None, [job.title, job.summary, job.required_qualifications])).lower()
    if not re.search(r"\bintern(ship)?\b|\bco-?op\b", text): return False
    if not any(term in text for term in MARKETING_TERMS): return False
    if re.search(r"software|developer|engineering|machine learning|data engineer", job.title, re.I): return False
    if re.search(r"\b2026\b", text) and not re.search(r"\b2027\b", text): return False
    if not re.search(r"\b2027\b", text): return False
    if re.search(r"full[- ]time permanent|regular full[- ]time", text): return False
    return True


def canonical_key(job: DiscoveredJob) -> str:
    if job.requisition_id:
        raw = f"req:{job.requisition_id.strip().lower()}"
    elif job.official_url:
        raw = f"url:{normalize_url(job.official_url)}"
    else:
        raw = "|".join([job.title.lower().strip(), (job.location or "").lower().strip(), job.internship_term])
    return hashlib.sha256(raw.encode()).hexdigest()


def _find_duplicate(session: Session, company_id: int, job: DiscoveredJob) -> Posting | None:
    key = canonical_key(job)
    exact = session.scalar(select(Posting).where(Posting.company_id == company_id, Posting.canonical_key == key))
    if exact: return exact
    candidates = session.scalars(select(Posting).where(Posting.company_id == company_id)).all()
    for candidate in candidates:
        title_score = SequenceMatcher(None, candidate.exact_title.lower(), job.title.lower()).ratio()
        same_context = (candidate.location or "").lower() == (job.location or "").lower() and candidate.internship_term == job.internship_term
        if title_score >= .92 and same_context: return candidate
    return None


def upsert_job(session: Session, company: Company, job: DiscoveredJob, run: SearchRun, profile: dict) -> tuple[Posting, str]:
    job = infer_fields(job)
    fingerprint = job.fingerprint()
    posting = _find_duplicate(session, company.id, job)
    now = utcnow()
    action = "duplicate"
    values = dict(
        requisition_id=job.requisition_id, exact_title=job.title, category=job.category,
        internship_term=job.internship_term, location=job.location, state=job.state,
        work_arrangement=job.work_arrangement, official_url=job.official_url,
        description_summary=job.summary, responsibilities=job.responsibilities,
        required_qualifications=job.required_qualifications, preferred_qualifications=job.preferred_qualifications,
        education_requirement=job.education_requirement, required_major=job.required_major,
        required_class_standing=job.required_class_standing, graduation_date_range=job.graduation_date_range,
        minimum_gpa=job.minimum_gpa, work_authorization_requirement=job.work_authorization_requirement,
        sponsorship_information=job.sponsorship_information, compensation=job.compensation,
        posting_date=job.posting_date, application_deadline=job.application_deadline,
        last_confirmed=now, last_seen_run_id=run.id, content_fingerprint=fingerprint,
    )
    if not posting:
        closure_status, _ = status_after_verification("new", seen=True, explicitly_closed=job.explicitly_closed, deadline=job.application_deadline)
        initial_status = "closed" if closure_status == "closed" else "new"
        posting = Posting(company_id=company.id, canonical_key=canonical_key(job), current_status=initial_status, **values)
        session.add(posting); session.flush()
        posting.changes.append(ChangeHistory(change_type="discovered", details="First discovered", new_fingerprint=fingerprint))
        action = "new"
    else:
        old = posting.content_fingerprint
        if old != fingerprint:
            for key, value in values.items(): setattr(posting, key, value)
            closure_status, posting.consecutive_failures = status_after_verification(
                "changed", seen=True, explicitly_closed=job.explicitly_closed, deadline=job.application_deadline)
            posting.current_status = "closed" if closure_status == "closed" else "changed"
            posting.changes.append(ChangeHistory(change_type="content_changed", details="Eligibility-relevant or public posting fields changed", old_fingerprint=old, new_fingerprint=fingerprint))
            action = "changed"
        else:
            posting.last_confirmed, posting.last_seen_run_id = now, run.id
            posting.current_status, posting.consecutive_failures = status_after_verification(
                posting.current_status, seen=True, explicitly_closed=job.explicitly_closed, deadline=job.application_deadline)
    for url in set(job.source_urls + [job.official_url]):
        existing = next((x for x in posting.sources if normalize_url(x.url) == normalize_url(url)), None)
        if existing: existing.last_seen = now
        else: posting.sources.append(SourceURL(url=url, source_type="official"))
    if action in {"new", "changed"}:
        posting.requirements.clear()
        requirement_values = (
            ("required_qualifications", job.required_qualifications, True),
            ("preferred_qualifications", job.preferred_qualifications, False),
            ("education", job.education_requirement, True), ("major", job.required_major, True),
            ("class_standing", job.required_class_standing, True),
            ("graduation_date", job.graduation_date_range, True),
            ("work_authorization", job.work_authorization_requirement, True),
            ("sponsorship", job.sponsorship_information, True),
        )
        posting.requirements.extend(Requirement(kind=kind, text=text, mandatory=mandatory)
                                    for kind, text, mandatory in requirement_values if text)
    result = assess(job, profile)
    matches, conflicts, missing = result.serialized()
    posting.assessments.append(EligibilityAssessment(
        classification=result.classification, confidence=result.confidence,
        matching_requirements=matches, conflicting_requirements=conflicts,
        missing_candidate_details=missing, explanation=result.explanation,
    ))
    return posting, action


def sync_companies(session: Session, configs: list[CompanyConfig]) -> dict[str, Company]:
    existing = {c.name: c for c in session.scalars(select(Company)).all()}
    for cfg in configs:
        company = existing.get(cfg.name) or Company(name=cfg.name)
        company.enabled, company.careers_url = cfg.enabled, cfg.careers_url
        company.ats_provider, company.ats_account = cfg.ats_provider, cfg.ats_account
        session.add(company); existing[cfg.name] = company
    session.flush()
    return existing


async def run_search(session: Session, configs: list[CompanyConfig], profile: dict, limit: int | None = None, mode: str = "full") -> SearchRun:
    enabled = [c for c in configs if c.enabled][:limit]
    run = SearchRun(mode=mode, companies_attempted=len(enabled)); session.add(run); session.flush()
    companies = sync_companies(session, configs)
    timeout = httpx.Timeout(20, connect=10)
    headers = {"User-Agent": "internship-tracker/0.1 (+local research; respectful public endpoints)", "Accept": "text/html,application/json"}
    try:
        async with httpx.AsyncClient(timeout=timeout, headers=headers, follow_redirects=True) as client:
            for cfg in enabled:
                adapter = adapter_for(cfg.ats_provider)(cfg, client)
                result = await adapter.fetch()
                accepted = 0
                for job in result.jobs:
                    if not job.official_url or not in_scope(infer_fields(job)): continue
                    upsert_job(session, companies[cfg.name], job, run, profile); accepted += 1
                session.add(CompanyCheck(search_run_id=run.id, company_id=companies[cfg.name].id,
                                         status=result.status, message=result.message, jobs_found=accepted))
                run.jobs_found += accepted
                session.commit()
        # Only a successfully checked company contributes missing-posting verification failures.
        checked_ids = {x.company_id for x in session.scalars(select(CompanyCheck).where(
            CompanyCheck.search_run_id == run.id, CompanyCheck.status == "successfully_checked")).all()}
        unseen = session.scalars(select(Posting).where(Posting.company_id.in_(checked_ids), Posting.last_seen_run_id != run.id,
                                                       Posting.current_status != "closed")).all() if checked_ids else []
        for posting in unseen:
            posting.current_status, posting.consecutive_failures = status_after_verification(
                posting.current_status, seen=False, consecutive_failures=posting.consecutive_failures,
                deadline=posting.application_deadline)
            posting.changes.append(ChangeHistory(change_type="verification_missed", details=f"Missed verification {posting.consecutive_failures} consecutive time(s)"))
        run.successful, run.completed_at = True, utcnow(); session.commit()
    except Exception as exc:
        run.error, run.completed_at = str(exc), utcnow(); run.successful = False; session.commit(); raise
    return run
