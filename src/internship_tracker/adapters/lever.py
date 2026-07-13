from .base import AdapterResult, BaseAdapter, DiscoveredJob, clean_html


class LeverAdapter(BaseAdapter):
    async def fetch(self) -> AdapterResult:
        if not self.company.ats_account:
            return AdapterResult("not_configured", message="Lever account identifier is missing")
        url = f"https://api.lever.co/v0/postings/{self.company.ats_account}?mode=json"
        try:
            data = await self.get_json(url)
        except PermissionError as exc:
            return AdapterResult("blocked", message=str(exc))
        except Exception as exc:
            return AdapterResult("technical_failure", message=str(exc))
        jobs = []
        for item in data:
            categories = item.get("categories") or {}
            lists = item.get("lists") or []
            jobs.append(DiscoveredJob(
                company=self.company.name, title=item.get("text", "Untitled role"),
                official_url=item.get("hostedUrl") or item.get("applyUrl"), requisition_id=item.get("id"),
                location=categories.get("location"), work_arrangement=categories.get("workplaceType") or "Unspecified",
                summary=clean_html(item.get("descriptionPlain") or item.get("description")),
                responsibilities=clean_html(" ".join(x.get("content", "") for x in lists)), source_urls=[url],
            ))
        return AdapterResult("successfully_checked", jobs, f"Lever public API returned {len(jobs)} jobs")

