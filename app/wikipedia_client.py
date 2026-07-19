"""Thin wrapper around Wikipedia's REST summary API (short description + hero image)."""

import httpx

BASE_URL = "https://en.wikipedia.org/api/rest_v1/page/summary"
USER_AGENT = "plant-tracker-personal-app/1.0 (contact: me@stevenjessup.com)"


async def get_summary(client: httpx.AsyncClient, title: str) -> dict | None:
    """Returns the page-summary dict, or None if the page is missing (404)
    or is a disambiguation page (type != "standard") — a 200 status alone
    doesn't mean the page is a usable match.
    """
    try:
        resp = await client.get(
            f"{BASE_URL}/{title.replace(' ', '_')}",
            headers={"User-Agent": USER_AGENT},
            timeout=10.0,
        )
    except httpx.HTTPError:
        return None
    if resp.status_code != 200:
        return None
    data = resp.json()
    if data.get("type") != "standard":
        return None
    return data
