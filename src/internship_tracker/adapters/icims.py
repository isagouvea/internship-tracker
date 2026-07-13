from .base import AdapterResult, BaseAdapter


class ICIMSAdapter(BaseAdapter):
    async def fetch(self) -> AdapterResult:
        return AdapterResult("not_configured", message="iCIMS has no universal public API; configure an approved company-specific endpoint")

