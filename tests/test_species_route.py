import app.main as main_module


def test_enrich_species_route_passes_query_params_through(client, monkeypatch):
    captured = {}

    async def fake_enrich(session, scientific_name, *, locale=None, country=None, fallback_common_name=None):
        captured.update(
            scientific_name=scientific_name, locale=locale, country=country,
            fallback_common_name=fallback_common_name,
        )
        return {
            "scientific_name": scientific_name, "gbif_usage_key": None, "family": None, "genus": None,
            "common_name": "Test Name", "common_name_source": "catalog",
            "description": None, "description_source": None, "photos": [],
            "care_light": None, "care_humidity": None, "care_min_temp_c": None, "care_max_temp_c": None,
            "care_soil": None, "from_cache": False,
        }

    monkeypatch.setattr(main_module.species_enrichment, "enrich_species", fake_enrich)

    response = client.get("/api/v1/species/enrich", params={
        "scientific_name": "Monstera deliciosa", "common_name": "Fallback", "locale": "en_US", "country": "US",
    })
    assert response.status_code == 200, response.text
    assert response.json()["common_name"] == "Test Name"
    assert captured == {
        "scientific_name": "Monstera deliciosa", "locale": "en_US",
        "country": "US", "fallback_common_name": "Fallback",
    }
