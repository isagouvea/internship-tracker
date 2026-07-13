from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "internships.db"
PROFILE_PATH = ROOT / "config" / "candidate_profile.yaml"
PROFILE_EXAMPLE_PATH = ROOT / "config" / "candidate_profile.example.yaml"
COMPANIES_PATH = ROOT / "config" / "companies.yaml"
DOCS_DIR = ROOT / "docs"

ELIGIBILITY = (
    "Likely eligible", "Possibly eligible", "Likely not eligible", "Unable to determine"
)
CHECK_STATUSES = (
    "successfully_checked", "partially_checked", "blocked", "unavailable",
    "not_configured", "technical_failure",
)
OPEN_STATUSES = ("open", "changed", "new", "may_have_closed")
MARKETING_TERMS = (
    "marketing", "brand", "social media", "content", "communications", "public relations",
    "advertising", "e-commerce", "ecommerce", "crm", "email", "consumer insights",
    "market research", "growth", "analytics", "event", "partnerships", "sales and marketing",
)

