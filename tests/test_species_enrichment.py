import pytest
from sqlmodel import Session

from app import species_enrichment
from app.db import engine
from app.models import Plant
from app.species_enrichment import enrich_species, rank_common_name


@pytest.fixture
def session(client):  # `client` fixture (conftest.py) guarantees a fresh DB per test
    with Session(engine) as s:
        yield s


def test_rank_common_name_catalog_match_wins(session):
    session.add(Plant(species_scientific="Monstera deliciosa", common_name="My Special Name"))
    session.commit()
    name, source = rank_common_name(
        session, "Monstera deliciosa",
        vernacular_names=[{"vernacularName": "Swiss Cheese Plant", "language": "eng"}],
        inaturalist_taxon={"preferred_common_name": "iNat Name"},
        fallback_common_name="Fallback Name",
        locale="en_US", country="US",
    )
    assert (name, source) == ("My Special Name", "catalog")


def test_rank_common_name_inaturalist_wins_without_catalog_match(session):
    name, source = rank_common_name(
        session, "Monstera deliciosa",
        vernacular_names=[{"vernacularName": "Swiss Cheese Plant", "language": "eng"}],
        inaturalist_taxon={"preferred_common_name": "iNat Name"},
        fallback_common_name="Fallback Name",
        locale="en_US", country="US",
    )
    assert (name, source) == ("iNat Name", "inaturalist")


def test_rank_common_name_gbif_vernacular_excludes_wrong_language_and_tie_breaks(session):
    name, source = rank_common_name(
        session, "Monstera deliciosa",
        vernacular_names=[
            {"vernacularName": "some long lowercase name", "language": "eng"},
            {"vernacularName": "Ceriman", "language": "eng", "country": "US"},
            {"vernacularName": "Nom Francais", "language": "fra"},
        ],
        inaturalist_taxon=None,
        fallback_common_name="Fallback Name",
        locale="en_US", country="US",
    )
    assert (name, source) == ("Ceriman", "gbif_vernacular")


def test_rank_common_name_fallback_used_last(session):
    name, source = rank_common_name(
        session, "Monstera deliciosa",
        vernacular_names=[], inaturalist_taxon=None,
        fallback_common_name="Fallback Name", locale="en_US", country="US",
    )
    assert (name, source) == ("Fallback Name", "plantnet_fallback")


def test_rank_common_name_none_when_everything_empty(session):
    name, source = rank_common_name(
        session, "Monstera deliciosa",
        vernacular_names=[], inaturalist_taxon=None,
        fallback_common_name=None, locale="en_US", country="US",
    )
    assert (name, source) == (None, None)


@pytest.mark.anyio
async def test_enrich_species_caches_and_reruns_ranking_fresh(session, monkeypatch):
    call_count = {"match": 0, "vernacular": 0}

    async def fake_match(client, name):
        call_count["match"] += 1
        return {
            "usageKey": 42, "canonicalName": "Monstera deliciosa",
            "family": "Araceae", "genus": "Monstera", "matchType": "EXACT",
        }

    async def fake_vernacular(client, usage_key):
        call_count["vernacular"] += 1
        return [{"vernacularName": "Swiss Cheese Plant", "language": "eng"}]

    async def fake_inat(client, name):
        return None

    async def fake_wiki(client, title):
        return {"type": "standard", "extract": "A vine.", "originalimage": {"source": "http://example.com/img.jpg"}}

    async def fake_trefle(client, name):
        return None

    monkeypatch.setattr(species_enrichment.gbif_client, "match_species", fake_match)
    monkeypatch.setattr(species_enrichment.gbif_client, "get_vernacular_names", fake_vernacular)
    monkeypatch.setattr(species_enrichment.inaturalist_client, "search_taxon", fake_inat)
    monkeypatch.setattr(species_enrichment.wikipedia_client, "get_summary", fake_wiki)
    monkeypatch.setattr(species_enrichment.trefle_client, "get_care_data", fake_trefle)

    result1 = await enrich_species(session, "Monstera deliciosa", locale="en_US", country="US")
    assert result1["common_name"] == "Swiss Cheese Plant"
    assert result1["common_name_source"] == "gbif_vernacular"
    assert result1["from_cache"] is False
    assert call_count["vernacular"] == 1

    session.add(Plant(species_scientific="Monstera deliciosa", common_name="My Catalog Name"))
    session.commit()

    result2 = await enrich_species(session, "Monstera deliciosa", locale="en_US", country="US")
    assert result2["from_cache"] is True
    assert result2["common_name"] == "My Catalog Name"
    assert result2["common_name_source"] == "catalog"
    assert call_count["vernacular"] == 1  # no re-fetch on cache hit
    assert call_count["match"] == 2  # GBIF match always re-runs (cheap, needed for cache key)


@pytest.mark.anyio
async def test_enrich_species_falls_back_when_gbif_match_fails(session, monkeypatch):
    async def fake_match_none(client, name):
        return None

    async def fake_inat(client, name):
        return None

    async def fake_wiki(client, title):
        return None

    async def fake_trefle(client, name):
        return None

    monkeypatch.setattr(species_enrichment.gbif_client, "match_species", fake_match_none)
    monkeypatch.setattr(species_enrichment.inaturalist_client, "search_taxon", fake_inat)
    monkeypatch.setattr(species_enrichment.wikipedia_client, "get_summary", fake_wiki)
    monkeypatch.setattr(species_enrichment.trefle_client, "get_care_data", fake_trefle)

    result = await enrich_species(session, "Fakeus speciesus", fallback_common_name="Fallback Name")
    assert result["scientific_name"] == "Fakeus speciesus"
    assert result["common_name"] == "Fallback Name"
    assert result["common_name_source"] == "plantnet_fallback"
