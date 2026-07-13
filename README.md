# Internship Tracker

A private-first, local application for finding and tracking Spring and Summer 2027 marketing internships. It checks configured official career sources, stores history in SQLite, applies transparent eligibility rules using a private candidate profile, and produces a sanitized static site that needs no backend.

The tracker never submits applications, signs into employer systems, defeats access controls, or requires a paid API. A company shown as blocked, partial, unavailable, unconfigured, or failed is never interpreted as having no internships.

## Quick start

Python 3.11 or newer is required.

```sh
make setup
make init
```

Then edit `config/candidate_profile.yaml`. It is copied from the example only when missing and is excluded by `.gitignore`. Unknown information should remain `unknown` or `null`; do not guess.

Run a small live check first:

```sh
make smoke
make report
make public-site
make privacy-check
make preview
```

Open <http://127.0.0.1:8000/> while preview is running. A complete search is `make update`; it searches, updates history, regenerates exports/site, and runs the privacy check.

## Commands

- `make setup` creates `.venv` and installs the package and test dependencies.
- `make init` creates `data/internships.db`, syncs company records, creates local directories, and copies the example profile if necessary.
- `make update` checks every enabled company sequentially with respectful timeouts/retries, then generates all outputs.
- `make smoke` performs a live check against at most five enabled companies. It does not regenerate the site automatically.
- `make public-site` rebuilds `docs/` from the existing database without network access.
- `make preview` serves `docs/` on localhost port 8000.
- `make report` creates `reports/latest.md`, `exports/internships.csv`, and `exports/internships.json` without searching.
- `make privacy-check` scans `docs/` for forbidden file types, private-profile field names, email addresses, phone numbers, private keys, and common secret formats.
- `make test` runs mocked tests; it does not use live websites.
- `make stats` prints database, run, status, and assessment counts.

All recipes stop with a nonzero exit code if a command fails.

## Candidate profile and eligibility

`config/candidate_profile.example.yaml` documents the fields. The real `config/candidate_profile.yaml` is private. Eligibility has exactly four possible outcomes: Likely eligible, Possibly eligible, Likely not eligible, and Unable to determine.

The engine compares mandatory education, major, GPA, class standing, graduation timing, and work-authorization requirements when they were extracted. Preferred qualifications do not create conflicts. Community-college enrollment is not a conflict unless an employer explicitly requires a four-year institution or another direct incompatibility exists. Each assessment records confidence from 0–100, matches, conflicts, missing details, and an explanation. These are deterministic rules, not AI judgments.

Review the official posting before applying: career pages can be incomplete and requirement extraction is intentionally conservative.

## Companies

`config/companies.yaml` contains the initial target list. Each entry supports:

```yaml
- name: Example Company
  enabled: true
  careers_url: https://example.com/careers
  internship_search_url: https://example.com/jobs
  ats_provider: greenhouse
  ats_account: example-board
  search_terms: [marketing, brand]
  preferred_locations: [Dallas–Fort Worth, Austin, Remote]
  notes: Public Greenhouse board
```

Names must be unique (case-insensitive), URLs must be HTTP(S), and the ATS provider must be one of `greenhouse`, `lever`, `smartrecruiters`, `workday`, `icims`, `generic`, or `teamworkonline`. Some initial entries deliberately lack an ATS identifier because one could not safely be assumed. They report `not_configured` rather than a false empty result.

To add a company, append a validated record, identify the official company-owned career site, prefer its public ATS board identifier, then run `make test` and `make smoke`. Search terms and preferred locations are stored per company for future adapter-specific querying; the shared scope filter enforces 2027 marketing internships.

## Search architecture

Adapters live under `src/internship_tracker/adapters/`:

- Greenhouse, Lever, and SmartRecruiters use documented/public JSON job-board endpoints.
- Generic fetches an official careers URL and accepts only structured `JobPosting` JSON-LD. A page that loads without structured results is marked partial, not empty.
- Workday and iCIMS are adapter boundaries with conservative configuration behavior. Workday tenants and iCIMS sites vary; they remain unconfigured until a company-specific public endpoint is verified.
- `registry.py` chooses an adapter. Unknown or secondary provider names fall back to conservative official-page parsing.

To add an ATS adapter, subclass `BaseAdapter`, return `AdapterResult` with one of the documented check statuses, normalize results into `DiscoveredJob`, register it in `registry.py`, and add mocked endpoint tests. Use ordinary HTTP first. Do not add CAPTCHA solving, authentication automation, browser-session persistence, proxy rotation, or access-control bypasses. Playwright is not installed; it may be added only for a verified public dynamic page after HTTP options are exhausted.

Pages and job text are untrusted input. The tracker parses limited fields and never executes page content or follows embedded instructions. HTTP requests have finite timeouts, redirects, retries, light backoff, and an identifying user agent. Checks run sequentially, avoiding request bursts.

## Database and history

The private SQLite database is `data/internships.db` and is gitignored. SQLAlchemy tables cover companies, postings, source URLs, extracted requirements, eligibility assessments, search runs, per-company checks, and change history. Only concise summaries and essential requirements are stored—not full raw pages or complete copyrighted job descriptions.

Deduplication first uses company plus requisition ID, then canonical official URL, then a high title-similarity threshold combined with location and term. One posting can retain several source URLs. Fingerprint changes create history records. Failed verification once produces `may_have_closed`; two consecutive misses following successful checks close a posting. Explicit closure, a passed deadline, or another reliable closure signal can close immediately. Closed records remain in the database and public history.

## Public site and privacy

`docs/` is a self-contained vanilla HTML/CSS/JavaScript site. Its relative URLs work both locally and at `https://USERNAME.github.io/internship-tracker/`. It includes responsive cards, accessible details, official links, summary counts, client-side search/filters, JSON, and separate open/eligible CSV downloads.

Publication uses a field allow-list in `publication.py`. It cannot serialize arbitrary ORM objects or the candidate profile. `state/public_state.json` contains only posting IDs, safe titles/company names, statuses, and fingerprints. Never put the database, `.env`, raw HTML, credentials, browser sessions, personal contact details, a résumé, or private notes under `docs/`.

Before committing site output:

```sh
make public-site
make privacy-check
git status --short
```

The privacy check is defense in depth, not permission to place private material in the repository.

## GitHub Pages

Commit the generated `docs/` directory and `.nojekyll`. In repository settings, enable Pages from the default branch and select `/docs` as the source folder. Do not commit `config/candidate_profile.yaml` or `data/internships.db`. Pages uses only sanitized generated artifacts; it cannot run searches.

## Daily scheduling

For a private local schedule, use cron or the operating system scheduler after manually confirming the virtual environment and profile. Example crontab entry (adjust the absolute path and time):

```cron
15 7 * * * cd /absolute/path/internship-tracker && make update >> logs/daily.log 2>&1
```

Create `logs/` locally; it is gitignored. Avoid overlapping runs. A hosted GitHub Action cannot access the private local profile/database unless secrets and state are deliberately uploaded, so local scheduling is the recommended privacy-preserving model. Publishing updated `docs/` still requires an intentional git commit/push workflow.

## Limitations and blocked sites

Career systems change, some render only in JavaScript, and many initial companies need verified tenant or board identifiers. Generic parsing does not crawl arbitrary links and search-engine discovery is not automated. This favors accuracy and official-source provenance over apparent coverage. Rate limiting, CAPTCHA, robots restrictions, authentication, or access denial results in a blocked/partial status and no bypass attempt. Re-run later or configure a verified public feed; never convert such a check into “no jobs.”

The application narrows discovered records to internships explicitly referring to 2027 and marketing-related categories, and excludes engineering/software roles, obvious permanent positions, and 2026-only results. Human review is still necessary for ambiguous dates, unpaid status, location availability, and application deadlines.

## Development

Run `make test`. Tests cover schema initialization, updates, deduplication, eligibility, closure rules, configuration validation, structured-feed parsing with mocked HTTP, sanitization, static generation, CSV/JSON exports, and privacy detection. Live sites are used only by `make smoke`/`make update`.

