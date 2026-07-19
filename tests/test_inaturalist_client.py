import httpx
import pytest

from app.inaturalist_client import search_taxon


class _FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=None, response=self)


class _FakeClient:
    def __init__(self, response):
        self._response = response

    async def get(self, *args, **kwargs):
        return self._response


@pytest.mark.anyio
async def test_search_taxon_prefers_exact_name_match():
    client = _FakeClient(_FakeResponse(200, {"results": [
        {"name": "Monstera adansonii", "preferred_common_name": "Swiss cheese vine"},
        {"name": "Monstera deliciosa", "preferred_common_name": "Swiss cheese plant"},
    ]}))
    result = await search_taxon(client, "Monstera deliciosa")
    assert result["preferred_common_name"] == "Swiss cheese plant"


@pytest.mark.anyio
async def test_search_taxon_falls_back_to_first_result():
    client = _FakeClient(_FakeResponse(200, {"results": [
        {"name": "Monstera sp.", "preferred_common_name": "Monstera"},
    ]}))
    result = await search_taxon(client, "Monstera deliciosa")
    assert result["preferred_common_name"] == "Monstera"


@pytest.mark.anyio
async def test_search_taxon_returns_none_on_empty_results():
    client = _FakeClient(_FakeResponse(200, {"results": []}))
    assert await search_taxon(client, "Fakeus speciesus") is None


@pytest.mark.anyio
async def test_search_taxon_returns_none_on_http_error():
    client = _FakeClient(_FakeResponse(500, {}))
    assert await search_taxon(client, "Monstera deliciosa") is None
