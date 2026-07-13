import json
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import AdapterResult, BaseAdapter, DiscoveredJob, clean_html, parse_date


class GenericAdapter(BaseAdapter):
    """Conservative adapter: reads official pages and only accepts JobPosting JSON-LD."""

    async def fetch(self) -> AdapterResult:
        url = self.company.internship_search_url or self.company.careers_url
        if not url:
            return AdapterResult("not_configured", message="No official careers URL configured")
        try:
            if not await self.robots_allowed(url):
                return AdapterResult("blocked", message="robots.txt disallows access to the configured careers URL")
            response = await self.client.get(url)
            if response.status_code in {401, 403, 429}:
                return AdapterResult("blocked", message=f"Official page returned HTTP {response.status_code}")
            response.raise_for_status()
        except Exception as exc:
            return AdapterResult("technical_failure", message=str(exc))
        soup, jobs = BeautifulSoup(response.text, "html.parser"), []
        for script in soup.select('script[type="application/ld+json"]'):
            try:
                values = json.loads(script.string or "null")
            except (ValueError, TypeError):
                continue
            values = values if isinstance(values, list) else [values]
            for item in values:
                if not isinstance(item, dict) or item.get("@type") != "JobPosting":
                    continue
                loc = item.get("jobLocation") or {}
                if isinstance(loc, list): loc = loc[0] if loc else {}
                address = loc.get("address") or {}
                job_url = item.get("url") or url
                jobs.append(DiscoveredJob(
                    company=self.company.name, title=item.get("title", "Untitled role"),
                    official_url=urljoin(url, job_url), requisition_id=(item.get("identifier") or {}).get("value") if isinstance(item.get("identifier"), dict) else None,
                    location=", ".join(filter(None, [address.get("addressLocality"), address.get("addressRegion")])),
                    state=address.get("addressRegion"), work_arrangement="Remote" if item.get("jobLocationType") == "TELECOMMUTE" else "Unspecified",
                    summary=clean_html(item.get("description")), posting_date=parse_date(item.get("datePosted")),
                    application_deadline=parse_date(item.get("validThrough")), source_urls=[url],
                ))
        status = "successfully_checked" if jobs else "partially_checked"
        message = f"Official page yielded {len(jobs)} structured JobPosting records" if jobs else "Official page loaded, but exposed no structured job feed; no zero-result claim made"
        return AdapterResult(status, jobs, message)
