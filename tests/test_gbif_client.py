import httpx
import pytest

from app.gbif_client import get_vernacular_names, match_species


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
    def __init__(self, responses):
        self._responses = list(responses)

    async def get(self, *args, **kwargs):
        return self._responses.pop(0)


@pytest.mark.anyio
async def test_match_species_returns_dict_on_exact_match():
    client = _FakeClient([_FakeResponse(200, {"usageKey": 123, "matchType": "EXACT", "canonicalName": "Foo bar"})])
    result = await match_species(client, "Foo bar")
    assert result["usageKey"] == 123


@pytest.mark.anyio
async def test_match_species_returns_none_when_no_match():
    client = _FakeClient([_FakeResponse(200, {"matchType": "NONE", "confidence": 100, "synonym": False})])
    assert await match_species(client, "Fakeus speciesus") is None


@pytest.mark.anyio
async def test_match_species_returns_none_on_http_error():
    client = _FakeClient([_FakeResponse(500, {})])
    assert await match_species(client, "Foo bar") is None


@pytest.mark.anyio
async def test_get_vernacular_names_paginates_until_end_of_records():
    client = _FakeClient([
        _FakeResponse(200, {"results": [{"vernacularName": "A"}], "endOfRecords": False}),
        _FakeResponse(200, {"results": [{"vernacularName": "B"}], "endOfRecords": True}),
    ])
    results = await get_vernacular_names(client, 123)
    assert [r["vernacularName"] for r in results] == ["A", "B"]


@pytest.mark.anyio
async def test_get_vernacular_names_keeps_partial_results_on_error():
    client = _FakeClient([
        _FakeResponse(200, {"results": [{"vernacularName": "A"}], "endOfRecords": False}),
        _FakeResponse(500, {}),
    ])
    results = await get_vernacular_names(client, 123)
    assert [r["vernacularName"] for r in results] == ["A"]
