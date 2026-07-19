import httpx

from app import plantnet_client
from app.plantnet_client import _pick_common_name, identify_species


class _FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self):
        return self._payload


def test_pick_common_name_returns_first_non_blank():
    assert _pick_common_name(["", "  ", "Swiss cheese plant", "Monstera"]) == "Swiss cheese plant"


def test_pick_common_name_returns_none_when_empty():
    assert _pick_common_name([]) is None
    assert _pick_common_name(["", "   "]) is None


def test_identify_species_parses_single_common_name_and_requests_lang(monkeypatch):
    monkeypatch.setattr(plantnet_client.settings, "plantnet_api_key", "test-key")
    captured = {}

    def fake_post(url, *, files, params, timeout):
        captured["params"] = params
        return _FakeResponse(
            200,
            {
                "results": [
                    {
                        "score": 0.87,
                        "species": {
                            "scientificNameWithoutAuthor": "Monstera deliciosa",
                            "commonNames": ["Swiss cheese plant", "Monstera"],
                        },
                    }
                ]
            },
        )

    monkeypatch.setattr(httpx, "post", fake_post)
    candidates, _raw = identify_species(b"fake-bytes", top_n=5)

    assert len(candidates) == 1
    assert candidates[0].common_name == "Swiss cheese plant"
    assert captured["params"]["lang"] == "en"
