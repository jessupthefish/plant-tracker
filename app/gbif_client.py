"""Thin wrapper around the GBIF Species API (taxonomy + vernacular names).

No API key required. Every function is fail-soft: on any HTTP error it
returns None/[] rather than raising, since this is enrichment data that
should never block an identification the user already has in hand.
"""

import httpx

BASE_URL = "https://api.gbif.org/v1"


async def match_species(client: httpx.AsyncClient, scientific_name: str) -> dict | None:
    """Resolves a scientific name to a GBIF taxon. Returns None if there's
    no usable match (network/HTTP failure, missing usageKey, or
    matchType == "NONE").

    Note: a SYNONYM match includes an acceptedUsageKey pointing to the
    currently-accepted name, which we deliberately don't re-resolve in v1 —
    known simplification, low priority edge case for a houseplant app.
    """
    try:
        resp = await client.get(f"{BASE_URL}/species/match", params={"name": scientific_name}, timeout=10.0)
        resp.raise_for_status()
    except httpx.HTTPError:
        return None
    data = resp.json()
    if "usageKey" not in data or data.get("matchType") == "NONE":
        return None
    return data


async def get_vernacular_names(client: httpx.AsyncClient, usage_key: int) -> list[dict]:
    """Fetches all pages of vernacularNames, bounded to 5 pages of 100 (500
    names max, plenty for ranking). Returns [] on failure, or whatever was
    gathered so far if a failure happens mid-pagination.
    """
    results: list[dict] = []
    offset = 0
    try:
        for _ in range(5):
            resp = await client.get(
                f"{BASE_URL}/species/{usage_key}/vernacularNames",
                params={"offset": offset, "limit": 100},
                timeout=10.0,
            )
            resp.raise_for_status()
            page = resp.json()
            results.extend(page.get("results", []))
            if page.get("endOfRecords", True):
                break
            offset += 100
    except httpx.HTTPError:
        pass
    return results
