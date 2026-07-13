import asyncio
import httpx

from internship_tracker.adapters.generic import GenericAdapter
from internship_tracker.config import CompanyConfig
from internship_tracker.search import in_scope
from internship_tracker.adapters.base import DiscoveredJob


def test_generic_adapter_uses_structured_official_data_only():
    html = '''<script type="application/ld+json">{"@type":"JobPosting","title":"Summer 2027 Marketing Intern","url":"https://example.com/apply","datePosted":"2026-09-01","description":"Marketing internship Summer 2027","jobLocation":{"address":{"addressLocality":"Austin","addressRegion":"TX"}}}</script>'''
    transport = httpx.MockTransport(lambda request: httpx.Response(200, text=html))
    cfg = CompanyConfig(name="Example", careers_url="https://example.com/jobs")
    async def execute():
        async with httpx.AsyncClient(transport=transport) as client:
            return await GenericAdapter(cfg, client).fetch()
    result = asyncio.run(execute())
    assert result.status == "successfully_checked" and len(result.jobs) == 1
    assert result.jobs[0].location == "Austin, TX"


def test_scope_rejects_wrong_year_and_engineering():
    assert in_scope(DiscoveredJob(company="X", title="Summer 2027 Marketing Intern", official_url="https://x", summary="marketing"))
    assert not in_scope(DiscoveredJob(company="X", title="Summer 2026 Marketing Intern", official_url="https://x"))
    assert not in_scope(DiscoveredJob(company="X", title="Summer 2027 Software Engineering Intern", official_url="https://x"))
