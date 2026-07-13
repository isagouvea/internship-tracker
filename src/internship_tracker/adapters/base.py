from __future__ import annotations

import asyncio
import hashlib
import json
import random
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from typing import Any
from urllib.parse import urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup

from ..config import CompanyConfig


@dataclass
class DiscoveredJob:
    company: str
    title: str
    official_url: str
    requisition_id: str | None = None
    location: str | None = None
    state: str | None = None
    work_arrangement: str = "Unspecified"
    internship_term: str = "Unspecified 2027"
    category: str = "Marketing"
    summary: str | None = None
    responsibilities: str | None = None
    required_qualifications: str | None = None
    preferred_qualifications: str | None = None
    education_requirement: str | None = None
    required_major: str | None = None
    required_class_standing: str | None = None
    graduation_date_range: str | None = None
    minimum_gpa: float | None = None
    work_authorization_requirement: str | None = None
    sponsorship_information: str | None = None
    compensation: str | None = None
    posting_date: date | None = None
    application_deadline: date | None = None
    source_urls: list[str] = field(default_factory=list)
    explicitly_closed: bool = False

    def fingerprint(self) -> str:
        public = asdict(self)
        public.pop("source_urls", None)
        parts = urlsplit(public["official_url"])
        public["official_url"] = urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), "", ""))
        return hashlib.sha256(json.dumps(public, sort_keys=True, default=str).encode()).hexdigest()


@dataclass
class AdapterResult:
    status: str
    jobs: list[DiscoveredJob] = field(default_factory=list)
    message: str | None = None


class BaseAdapter:
    def __init__(self, company: CompanyConfig, client: httpx.AsyncClient):
        self.company, self.client = company, client

    async def fetch(self) -> AdapterResult:
        raise NotImplementedError

    async def get_json(self, url: str, **kwargs) -> Any:
        last = None
        for attempt in range(3):
            try:
                if attempt:
                    await asyncio.sleep((2 ** attempt) + random.random())
                response = await self.client.get(url, **kwargs)
                if response.status_code in {401, 403, 429}:
                    raise PermissionError(f"HTTP {response.status_code}")
                response.raise_for_status()
                return response.json()
            except (httpx.HTTPError, ValueError) as exc:
                last = exc
        raise RuntimeError(f"Request failed after retries: {last}")

    async def robots_allowed(self, url: str) -> bool:
        parts = urlsplit(url)
        robots_url = urlunsplit((parts.scheme, parts.netloc, "/robots.txt", "", ""))
        try:
            response = await self.client.get(robots_url)
            if response.status_code == 404:
                return True
            response.raise_for_status()
            parser = RobotFileParser(); parser.set_url(robots_url); parser.parse(response.text.splitlines())
            return parser.can_fetch(self.client.headers.get("User-Agent", "internship-tracker"), url)
        except httpx.HTTPError:
            # The robots exclusion standard treats an unavailable robots file as no declared restriction.
            return True


def clean_html(value: str | None, limit: int = 1800) -> str | None:
    if not value:
        return None
    text = BeautifulSoup(value, "html.parser").get_text(" ", strip=True)
    return " ".join(text.split())[:limit]


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        return None
