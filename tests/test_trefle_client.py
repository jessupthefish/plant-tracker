import pytest

from app import trefle_client
from app.trefle_client import get_care_data


class _FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


class _FakeClient:
    def __init__(self, responses=None, raise_on_get=False):
        self._responses = list(responses or [])
        self._raise_on_get = raise_on_get

    async def get(self, *args, **kwargs):
        if self._raise_on_get:
            raise Exception("simulated timeout/SSL failure")
        return self._responses.pop(0)


@pytest.mark.anyio
async def test_get_care_data_returns_none_without_api_key(monkeypatch):
    monkeypatch.setattr(trefle_client.settings, "trefle_api_key", "")
    assert await get_care_data(_FakeClient(), "Monstera deliciosa") is None


@pytest.mark.anyio
async def test_get_care_data_returns_none_on_any_failure(monkeypatch):
    monkeypatch.setattr(trefle_client.settings, "trefle_api_key", "test-key")
    client = _FakeClient(raise_on_get=True)
    assert await get_care_data(client, "Monstera deliciosa") is None


@pytest.mark.anyio
async def test_get_care_data_returns_parsed_dict_on_success(monkeypatch):
    monkeypatch.setattr(trefle_client.settings, "trefle_api_key", "test-key")
    client = _FakeClient(responses=[
        _FakeResponse(200, {"data": [{"id": 1}]}),
        _FakeResponse(200, {"data": {"growth": {
            "light": 8,
            "atmospheric_humidity": 5,
            "minimum_temperature": {"deg_c": 15},
            "maximum_temperature": {"deg_c": 30},
            "soil_nutriments": ["loam"],
        }}}),
    ])
    result = await get_care_data(client, "Monstera deliciosa")
    assert result == {
        "light": 8, "humidity": 5, "min_temp_c": 15, "max_temp_c": 30, "soil": "loam",
    }
