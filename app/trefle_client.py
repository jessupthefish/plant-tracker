"""Optional wrapper around the Trefle API for supplementary care data.

Trefle self-describes as beta with a documented history of outages and
signs of maintainer inactivity, so this must never block the rest of the
enrichment response. Every failure mode (no key configured, timeout, 401,
SSL error, malformed JSON) returns None. Perenual (perenual.com) is a
documented fallback alternative if Trefle proves too unreliable in
practice — not built now, just noted here.
"""

import httpx

from app.config import settings

BASE_URL = "https://trefle.io/api/v1"


async def get_care_data(client: httpx.AsyncClient, scientific_name: str) -> dict | None:
    if not settings.trefle_api_key:
        return None
    try:
        search = await client.get(
            f"{BASE_URL}/plants/search",
            params={"token": settings.trefle_api_key, "q": scientific_name},
            timeout=10.0,
        )
        search.raise_for_status()
        hits = search.json().get("data") or []
        if not hits:
            return None
        detail = await client.get(
            f"{BASE_URL}/plants/{hits[0]['id']}",
            params={"token": settings.trefle_api_key},
            timeout=10.0,
        )
        detail.raise_for_status()
        growth = (detail.json().get("data") or {}).get("growth") or {}
        return {
            "light": growth.get("light"),
            "humidity": growth.get("atmospheric_humidity"),
            "min_temp_c": (growth.get("minimum_temperature") or {}).get("deg_c"),
            "max_temp_c": (growth.get("maximum_temperature") or {}).get("deg_c"),
            "soil": ", ".join(growth.get("soil_nutriments") or []) or None,
        }
    except Exception:  # noqa: BLE001 — intentional: Trefle is best-effort only
        return None
