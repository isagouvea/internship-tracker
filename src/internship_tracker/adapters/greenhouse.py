from .base import AdapterResult, BaseAdapter, DiscoveredJob, clean_html, parse_date


class GreenhouseAdapter(BaseAdapter):
    async def fetch(self) -> AdapterResult:
        if not self.company.ats_account:
            return AdapterResult("not_configured", message="Greenhouse board identifier is missing")
        url = f"https://boards-api.greenhouse.io/v1/boards/{self.company.ats_account}/jobs?content=true"
        try:
            data = await self.get_json(url)
        except PermissionError as exc:
            return AdapterResult("blocked", message=str(exc))
        except Exception as exc:
            return AdapterResult("technical_failure", message=str(exc))
        jobs = []
        for item in data.get("jobs", []):
            metadata = {str(x.get("name", "")).lower(): x.get("value") for x in item.get("metadata") or []}
            jobs.append(DiscoveredJob(
                company=self.company.name, title=item.get("title", "Untitled role"),
                official_url=item.get("absolute_url"), requisition_id=str(item.get("id")),
                location=(item.get("location") or {}).get("name"), summary=clean_html(item.get("content")),
                posting_date=parse_date(item.get("updated_at")), source_urls=[url],
                compensation=str(metadata.get("salary range")) if metadata.get("salary range") else None,
            ))
        return AdapterResult("successfully_checked", jobs, f"Greenhouse public API returned {len(jobs)} jobs")

