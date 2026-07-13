from __future__ import annotations

import asyncio
import json
import shutil
from pathlib import Path

import typer
from sqlalchemy import func, select

from .config import initialize_profile, load_companies, load_profile
from .constants import DB_PATH, DOCS_DIR, PROFILE_PATH, ROOT
from .database import initialize_database, session_factory
from .models import CompanyCheck, EligibilityAssessment, Posting, SearchRun
from .publication import generate_site, privacy_check, write_exports, write_report
from .search import run_search, sync_companies

app = typer.Typer(no_args_is_help=True, help="Private-first 2027 marketing internship tracker")


@app.command("init")
def init_command(db: Path = typer.Option(DB_PATH)):
    created = initialize_profile()
    factory = session_factory(db)
    with factory() as session:
        configs = load_companies(); sync_companies(session, configs); session.commit()
    for directory in (ROOT / "state", ROOT / "reports", ROOT / "exports", DOCS_DIR): directory.mkdir(parents=True, exist_ok=True)
    typer.echo(f"Database initialized at {db}")
    typer.echo("Created private candidate profile; review it before searching." if created else "Private candidate profile already exists; left unchanged.")


@app.command("update")
def update_command(limit: int | None = typer.Option(None, min=1), smoke: bool = typer.Option(False), db: Path = typer.Option(DB_PATH)):
    if smoke and (limit is None or limit > 5): limit = 5
    if not PROFILE_PATH.exists(): raise typer.BadParameter("Run init and edit config/candidate_profile.yaml first")
    configs, profile = load_companies(), load_profile()
    with session_factory(db)() as session:
        run = asyncio.run(run_search(session, configs, profile, limit=limit, mode="smoke" if smoke else "full"))
        typer.echo(f"Run {run.id}: checked {run.companies_attempted} companies; accepted {run.jobs_found} in-scope postings")
        checks = session.execute(select(CompanyCheck.status, func.count()).where(CompanyCheck.search_run_id == run.id).group_by(CompanyCheck.status)).all()
        for status, count in checks: typer.echo(f"  {status}: {count}")


@app.command("public-site")
def site_command(db: Path = typer.Option(DB_PATH), docs: Path = typer.Option(DOCS_DIR)):
    with session_factory(db)() as session:
        jobs, _ = generate_site(session, docs)
    typer.echo(f"Generated static site with {len(jobs)} historical postings at {docs}")


@app.command("report")
def report_command(db: Path = typer.Option(DB_PATH)):
    with session_factory(db)() as session:
        from .publication import collect_public_jobs
        jobs = collect_public_jobs(session)
        write_exports(jobs, ROOT / "exports")
        write_report(session, ROOT / "reports" / "latest.md")
    typer.echo(f"Wrote CSV/JSON exports and report for {len(jobs)} postings")


@app.command("privacy-check")
def privacy_command(docs: Path = typer.Option(DOCS_DIR)):
    problems = privacy_check(docs)
    if problems:
        for problem in problems: typer.echo(f"ERROR: {problem}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Privacy check passed for {docs}")


@app.command("stats")
def stats_command(db: Path = typer.Option(DB_PATH)):
    if not db.exists(): raise typer.BadParameter("Database does not exist; run init")
    with session_factory(db)() as session:
        totals = {
            "postings": session.scalar(select(func.count(Posting.id))) or 0,
            "open": session.scalar(select(func.count(Posting.id)).where(Posting.current_status != "closed")) or 0,
            "closed": session.scalar(select(func.count(Posting.id)).where(Posting.current_status == "closed")) or 0,
            "search_runs": session.scalar(select(func.count(SearchRun.id))) or 0,
            "successful_runs": session.scalar(select(func.count(SearchRun.id)).where(SearchRun.successful.is_(True))) or 0,
        }
        eligibility = dict(session.execute(select(EligibilityAssessment.classification, func.count()).group_by(EligibilityAssessment.classification)).all())
    typer.echo(json.dumps({**totals, "assessments": eligibility}, indent=2))


if __name__ == "__main__": app()

