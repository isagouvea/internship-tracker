from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Company(Base):
    __tablename__ = "companies"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    careers_url: Mapped[str | None] = mapped_column(Text)
    ats_provider: Mapped[str] = mapped_column(String(50), default="generic")
    ats_account: Mapped[str | None] = mapped_column(String(200))
    postings: Mapped[list["Posting"]] = relationship(back_populates="company")


class Posting(Base):
    __tablename__ = "postings"
    __table_args__ = (UniqueConstraint("company_id", "canonical_key", name="uq_company_posting"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    requisition_id: Mapped[str | None] = mapped_column(String(200), index=True)
    canonical_key: Mapped[str] = mapped_column(String(64), index=True)
    exact_title: Mapped[str] = mapped_column(String(500))
    category: Mapped[str] = mapped_column(String(100), default="Marketing")
    internship_term: Mapped[str] = mapped_column(String(50), default="Unspecified 2027")
    location: Mapped[str | None] = mapped_column(String(500))
    state: Mapped[str | None] = mapped_column(String(80))
    work_arrangement: Mapped[str] = mapped_column(String(30), default="Unspecified")
    official_url: Mapped[str] = mapped_column(Text)
    description_summary: Mapped[str | None] = mapped_column(Text)
    responsibilities: Mapped[str | None] = mapped_column(Text)
    required_qualifications: Mapped[str | None] = mapped_column(Text)
    preferred_qualifications: Mapped[str | None] = mapped_column(Text)
    education_requirement: Mapped[str | None] = mapped_column(Text)
    required_major: Mapped[str | None] = mapped_column(String(300))
    required_class_standing: Mapped[str | None] = mapped_column(String(200))
    graduation_date_range: Mapped[str | None] = mapped_column(String(200))
    minimum_gpa: Mapped[float | None] = mapped_column(Float)
    work_authorization_requirement: Mapped[str | None] = mapped_column(Text)
    sponsorship_information: Mapped[str | None] = mapped_column(Text)
    compensation: Mapped[str | None] = mapped_column(String(300))
    posting_date: Mapped[date | None] = mapped_column(Date)
    application_deadline: Mapped[date | None] = mapped_column(Date)
    first_found: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_confirmed: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    current_status: Mapped[str] = mapped_column(String(40), default="new", index=True)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0)
    content_fingerprint: Mapped[str] = mapped_column(String(64))
    last_seen_run_id: Mapped[int | None] = mapped_column(ForeignKey("search_runs.id"))
    company: Mapped[Company] = relationship(back_populates="postings")
    sources: Mapped[list["SourceURL"]] = relationship(cascade="all, delete-orphan")
    requirements: Mapped[list["Requirement"]] = relationship(cascade="all, delete-orphan")
    assessments: Mapped[list["EligibilityAssessment"]] = relationship(cascade="all, delete-orphan")
    changes: Mapped[list["ChangeHistory"]] = relationship(cascade="all, delete-orphan")


class SourceURL(Base):
    __tablename__ = "source_urls"
    __table_args__ = (UniqueConstraint("posting_id", "url", name="uq_posting_source"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    posting_id: Mapped[int] = mapped_column(ForeignKey("postings.id"), index=True)
    url: Mapped[str] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String(50), default="official")
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Requirement(Base):
    __tablename__ = "requirements"
    id: Mapped[int] = mapped_column(primary_key=True)
    posting_id: Mapped[int] = mapped_column(ForeignKey("postings.id"), index=True)
    kind: Mapped[str] = mapped_column(String(80))
    text: Mapped[str] = mapped_column(Text)
    mandatory: Mapped[bool] = mapped_column(Boolean, default=True)


class EligibilityAssessment(Base):
    __tablename__ = "eligibility_assessments"
    id: Mapped[int] = mapped_column(primary_key=True)
    posting_id: Mapped[int] = mapped_column(ForeignKey("postings.id"), index=True)
    classification: Mapped[str] = mapped_column(String(40), index=True)
    confidence: Mapped[int] = mapped_column(Integer)
    matching_requirements: Mapped[str] = mapped_column(Text, default="[]")
    conflicting_requirements: Mapped[str] = mapped_column(Text, default="[]")
    missing_candidate_details: Mapped[str] = mapped_column(Text, default="[]")
    explanation: Mapped[str] = mapped_column(Text)
    assessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SearchRun(Base):
    __tablename__ = "search_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    mode: Mapped[str] = mapped_column(String(30), default="full")
    successful: Mapped[bool] = mapped_column(Boolean, default=False)
    companies_attempted: Mapped[int] = mapped_column(Integer, default=0)
    jobs_found: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text)


class CompanyCheck(Base):
    __tablename__ = "company_checks"
    id: Mapped[int] = mapped_column(primary_key=True)
    search_run_id: Mapped[int] = mapped_column(ForeignKey("search_runs.id"), index=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    status: Mapped[str] = mapped_column(String(40))
    message: Mapped[str | None] = mapped_column(Text)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    jobs_found: Mapped[int] = mapped_column(Integer, default=0)


class ChangeHistory(Base):
    __tablename__ = "change_history"
    id: Mapped[int] = mapped_column(primary_key=True)
    posting_id: Mapped[int] = mapped_column(ForeignKey("postings.id"), index=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    change_type: Mapped[str] = mapped_column(String(50))
    details: Mapped[str] = mapped_column(Text)
    old_fingerprint: Mapped[str | None] = mapped_column(String(64))
    new_fingerprint: Mapped[str | None] = mapped_column(String(64))

