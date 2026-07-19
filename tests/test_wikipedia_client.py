import pytest

from app.wikipedia_client import get_summary


class _FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


class _FakeClient:
    def __init__(self, response):
        self._response = response

    async def get(self, *args, **kwargs):
        return self._response


@pytest.mark.anyio
async def test_get_summary_returns_data_for_standard_page():
    client = _FakeClient(_FakeResponse(200, {"type": "standard", "extract": "A species of plant."}))
    result = await get_summary(client, "Monstera_deliciosa")
    assert result["extract"] == "A species of plant."


@pytest.mark.anyio
async def test_get_summary_returns_none_for_disambiguation_page():
    client = _FakeClient(_FakeResponse(200, {"type": "disambiguation", "extract": "Monstera may refer to..."}))
    assert await get_summary(client, "Monstera") is None


@pytest.mark.anyio
async def test_get_summary_returns_none_on_404():
    client = _FakeClient(_FakeResponse(404, {"type": "https://mediawiki.org/wiki/HyperSwitch/errors/not_found"}))
    assert await get_summary(client, "Fakeus_speciesus") is None
