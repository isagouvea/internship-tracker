from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

import yaml

from .constants import COMPANIES_PATH, PROFILE_EXAMPLE_PATH, PROFILE_PATH


@dataclass
class CompanyConfig:
    name: str
    enabled: bool = True
    careers_url: str | None = None
    internship_search_url: str | None = None
    ats_provider: str = "generic"
    ats_account: str | None = None
    search_terms: list[str] = field(default_factory=lambda: ["marketing"])
    preferred_locations: list[str] = field(default_factory=list)
    notes: str | None = None


def _read_yaml(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Missing configuration: {path}")
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def load_companies(path: Path = COMPANIES_PATH) -> list[CompanyConfig]:
    raw = _read_yaml(path)
    if not isinstance(raw.get("companies"), list):
        raise ValueError("companies.yaml must contain a 'companies' list")
    result, names = [], set()
    allowed = {"generic", "greenhouse", "lever", "smartrecruiters", "workday", "icims", "teamworkonline"}
    for i, item in enumerate(raw["companies"]):
        if not isinstance(item, dict) or not str(item.get("name", "")).strip():
            raise ValueError(f"Company entry {i + 1} requires a name")
        key = item["name"].strip().casefold()
        if key in names:
            raise ValueError(f"Duplicate company name: {item['name']}")
        names.add(key)
        provider = str(item.get("ats_provider") or "generic").lower()
        if provider not in allowed:
            raise ValueError(f"Unsupported ATS provider for {item['name']}: {provider}")
        for url_key in ("careers_url", "internship_search_url"):
            url = item.get(url_key)
            if url and urlparse(str(url)).scheme not in {"http", "https"}:
                raise ValueError(f"{item['name']} has invalid {url_key}")
        result.append(CompanyConfig(
            name=item["name"].strip(), enabled=bool(item.get("enabled", True)),
            careers_url=item.get("careers_url"), internship_search_url=item.get("internship_search_url"),
            ats_provider=provider, ats_account=item.get("ats_account"),
            search_terms=list(item.get("search_terms") or ["marketing"]),
            preferred_locations=list(item.get("preferred_locations") or []), notes=item.get("notes"),
        ))
    return result


def load_profile(path: Path = PROFILE_PATH) -> dict:
    return _read_yaml(path)


def initialize_profile(destination: Path = PROFILE_PATH) -> bool:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        return False
    shutil.copyfile(PROFILE_EXAMPLE_PATH, destination)
    return True

