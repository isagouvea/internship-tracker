from .base import AdapterResult, BaseAdapter, DiscoveredJob, clean_html, parse_date


class SmartRecruitersAdapter(BaseAdapter):
    async def fetch(self) -> AdapterResult:
        if not self.company.ats_account:
            return AdapterResult("not_configured", message="SmartRecruiters company identifier is missing")
        url = f"https://api.smartrecruiters.com/v1/companies/{self.company.ats_account}/postings?limit=100"
        try:
            data = await self.get_json(url)
        except PermissionError as exc:
            return AdapterResult("blocked", message=str(exc))
        except Exception as exc:
            return AdapterResult("technical_failure", message=str(exc))
        jobs = []
        for item in data.get("content", []):
            loc = item.get("location") or {}
            jobs.append(DiscoveredJob(
                company=self.company.name, title=item.get("name", "Untitled role"),
                official_url=item.get("ref") or f"https://jobs.smartrecruiters.com/{self.company.ats_account}/{item.get('id')}",
                requisition_id=item.get("id"), location=", ".join(filter(None, [loc.get("city"), loc.get("region"), loc.get("country")])),
                state=loc.get("region"), work_arrangement="Remote" if loc.get("remote") else "Unspecified",
                posting_date=parse_date(item.get("releasedDate")), summary=clean_html(item.get("jobAd", {}).get("sections", {}).get("jobDescription", {}).get("text")),
                source_urls=[url],
            ))
        return AdapterResult("successfully_checked", jobs, f"SmartRecruiters public API returned {len(jobs)} jobs")

