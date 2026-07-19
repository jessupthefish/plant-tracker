"""Thin wrapper around the iNaturalist taxa API (curated common name + photos).

iNaturalist asks callers to stay <=60 req/min and <10k/day with a
descriptive User-Agent. This app only calls it once per user-initiated
"identify" action, well within bounds — no rate-limiting logic needed.
"""

import httpx

BASE_URL = "https://api.inaturalist.org/v1"
USER_AGENT = "plant-tracker-personal-app/1.0 (contact: me@stevenjessup.com)"


async def search_taxon(client: httpx.AsyncClient, scientific_name: str) -> dict | None:
    """Returns the best-matching taxon dict, or None on failure/no results.

    Prefers an exact case-insensitive name match among results, falling
    back to the top (most relevant) result otherwise.
    """
    try:
        resp = await client.get(
            f"{BASE_URL}/taxa",
            params={"q": scientific_name},
            headers={"User-Agent": USER_AGENT},
            timeout=10.0,
        )
        resp.raise_for_status()
    except httpx.HTTPError:
        return None
    results = resp.json().get("results") or []
    if not results:
        return None
    needle = scientific_name.strip().lower()
    for r in results:
        if (r.get("name") or "").strip().lower() == needle:
            return r
    return results[0]
