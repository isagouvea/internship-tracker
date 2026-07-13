from .base import AdapterResult, BaseAdapter


class WorkdayAdapter(BaseAdapter):
    async def fetch(self) -> AdapterResult:
        # Account format: https://tenant.wdN.myworkdayjobs.com/wday/cxs/tenant/site
        if not self.company.ats_account or not self.company.ats_account.startswith("https://"):
            return AdapterResult("not_configured", message="Workday CXS base endpoint is missing")
        return AdapterResult("not_configured", message="Workday endpoint configured but requires site-specific payload settings; use Generic or extend adapter")

