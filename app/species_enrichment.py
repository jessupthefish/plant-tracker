"""Combines GBIF, iNaturalist, Wikipedia, and (optionally) Trefle into a
single enriched species record: an authoritative common name, a short
description, and a couple of quality photos.

Cache-first: raw source data is cached indefinitely per scientific name
(SpeciesEnrichment model) since it barely changes. Common-name RANKING is
re-run fresh on every call using the cached raw data, because it also
depends on the caller's locale/country and — top priority — the user's own
Plant catalog, which can change between calls even when cached taxonomy
data hasn't.
"""

import asyncio
import json
from datetime import UTC, datetime

import httpx
from sqlmodel import Session, func, select

from app import gbif_client, inaturalist_client, trefle_client, wikipedia_client
from app.models import Plant, SpeciesEnrichment

LOCALE_TO_GBIF_LANG = {
    "en": "eng", "es": "spa", "fr": "fra", "de": "deu", "pt": "por", "it": "ita",
}
DEFAULT_GBIF_LANG = "eng"

COUNTRY_ALIASES = {
    "us": "US", "usa": "US", "united states": "US", "united states of america": "US",
    "uk": "GB", "united kingdom": "GB", "great britain": "GB", "england": "GB",
    "canada": "CA", "australia": "AU", "germany": "DE", "france": "FR",
    "spain": "ES", "portugal": "PT", "italy": "IT", "mexico": "MX",
}


def _map_locale(locale: str | None) -> str:
    if not locale:
        return DEFAULT_GBIF_LANG
    primary = locale.replace("-", "_").split("_")[0].strip().lower()
    return LOCALE_TO_GBIF_LANG.get(primary, DEFAULT_GBIF_LANG)


def _normalize_country(country: str | None) -> str | None:
    if not country:
        return None
    cleaned = country.strip().lower()
    if cleaned in COUNTRY_ALIASES:
        return COUNTRY_ALIASES[cleaned]
    if len(cleaned) == 2 and cleaned.isalpha():
        return cleaned.upper()
    return None


def _catalog_common_name(session: Session, canonical_name: str) -> str | None:
    stmt = (
        select(Plant)
        .where(func.lower(Plant.species_scientific) == canonical_name.lower())
        .where(Plant.common_name.is_not(None))
        .where(Plant.common_name != "")
        .order_by(Plant.updated_at.desc())
    )
    plant = session.exec(stmt).first()
    return plant.common_name if plant else None


def _best_gbif_vernacular(vernacular_names: list[dict], gbif_lang: str, country_code: str | None) -> str | None:
    eligible = [v for v in vernacular_names if v.get("language") == gbif_lang and v.get("vernacularName")]
    if not eligible:
        return None

    def score(v: dict) -> tuple:
        country_match = 0 if v.get("country") == country_code and country_code else 1
        name = v["vernacularName"].strip()
        title_case_bonus = 0 if name.istitle() else 1
        return (country_match, title_case_bonus, len(name), name.lower())

    eligible.sort(key=score)
    return eligible[0]["vernacularName"].strip()


def rank_common_name(
    session: Session,
    canonical_name: str,
    vernacular_names: list[dict],
    inaturalist_taxon: dict | None,
    fallback_common_name: str | None,
    locale: str | None,
    country: str | None,
) -> tuple[str | None, str | None]:
    """Returns (common_name, source). Ordered rule set — first rule that
    produces a name wins; no numeric scoring across tiers.

    1. Existing catalog match (consistency with what's already saved).
    2. iNaturalist's curated preferred_common_name.
    3. GBIF vernacular name, filtered to locale-matched language, then
       tie-broken by country match, title-case, shortness, alphabetical.
    4. Pl@ntNet's own fallback pick.
    5. None.
    """
    catalog_name = _catalog_common_name(session, canonical_name)
    if catalog_name:
        return catalog_name, "catalog"

    if inaturalist_taxon and inaturalist_taxon.get("preferred_common_name"):
        return inaturalist_taxon["preferred_common_name"].strip(), "inaturalist"

    gbif_lang = _map_locale(locale)
    country_code = _normalize_country(country)
    gbif_name = _best_gbif_vernacular(vernacular_names, gbif_lang, country_code)
    if gbif_name:
        return gbif_name, "gbif_vernacular"

    if fallback_common_name:
        return fallback_common_name.strip(), "plantnet_fallback"

    return None, None


def _build_photos(inaturalist_taxon: dict | None, wikipedia_summary: dict | None) -> list[dict]:
    photos: list[dict] = []
    if inaturalist_taxon:
        default_photo = inaturalist_taxon.get("default_photo")
        if default_photo and default_photo.get("medium_url"):
            photos.append({
                "url": default_photo["medium_url"],
                "source": "inaturalist",
                "attribution": default_photo.get("attribution"),
                "license_code": default_photo.get("license_code"),
            })
        for extra in (inaturalist_taxon.get("taxon_photos") or [])[1:3]:
            photo = extra.get("photo") or {}
            if photo.get("medium_url") and len(photos) < 3:
                photos.append({
                    "url": photo["medium_url"],
                    "source": "inaturalist",
                    "attribution": photo.get("attribution"),
                    "license_code": photo.get("license_code"),
                })
    if not photos and wikipedia_summary:
        image = wikipedia_summary.get("originalimage") or wikipedia_summary.get("thumbnail")
        if image and image.get("source"):
            photos.append({"url": image["source"], "source": "wikipedia", "attribution": None, "license_code": None})
    return photos[:3]


async def _empty_list() -> list:
    return []


async def _fetch_raw(client: httpx.AsyncClient, canonical_name: str, usage_key: int | None) -> dict:
    vernacular_names, inat_taxon, wiki_summary, trefle_care = await asyncio.gather(
        gbif_client.get_vernacular_names(client, usage_key) if usage_key else _empty_list(),
        inaturalist_client.search_taxon(client, canonical_name),
        wikipedia_client.get_summary(client, canonical_name),
        trefle_client.get_care_data(client, canonical_name),
    )
    return {
        "vernacular_names": vernacular_names,
        "inaturalist_taxon": inat_taxon,
        "wikipedia_summary": wiki_summary,
        "trefle_care": trefle_care,
    }


async def enrich_species(
    session: Session,
    scientific_name: str,
    *,
    locale: str | None = None,
    country: str | None = None,
    fallback_common_name: str | None = None,
) -> dict:
    scientific_name = scientific_name.strip()
    try:
        async with httpx.AsyncClient() as client:
            gbif_match = await gbif_client.match_species(client, scientific_name)
            canonical_name = (gbif_match or {}).get("canonicalName") or scientific_name
            usage_key = (gbif_match or {}).get("usageKey")
            cache_key = canonical_name.lower()

            cached = session.get(SpeciesEnrichment, cache_key)
            if cached:
                raw = json.loads(cached.raw_data)
                from_cache = True
            else:
                raw = await _fetch_raw(client, canonical_name, usage_key)
                session.add(SpeciesEnrichment(
                    scientific_name=cache_key,
                    gbif_usage_key=usage_key,
                    raw_data=json.dumps(raw),
                    fetched_at=datetime.now(UTC),
                ))
                session.commit()
                from_cache = False

        common_name, common_name_source = rank_common_name(
            session, canonical_name, raw["vernacular_names"], raw["inaturalist_taxon"],
            fallback_common_name, locale, country,
        )
        wiki_summary = raw["wikipedia_summary"]
        trefle_care = raw["trefle_care"] or {}
        return {
            "scientific_name": canonical_name,
            "gbif_usage_key": usage_key,
            "family": (gbif_match or {}).get("family"),
            "genus": (gbif_match or {}).get("genus"),
            "common_name": common_name,
            "common_name_source": common_name_source,
            "description": (wiki_summary or {}).get("extract"),
            "description_source": "wikipedia" if wiki_summary else None,
            "photos": _build_photos(raw["inaturalist_taxon"], wiki_summary),
            "care_light": trefle_care.get("light"),
            "care_humidity": trefle_care.get("humidity"),
            "care_min_temp_c": trefle_care.get("min_temp_c"),
            "care_max_temp_c": trefle_care.get("max_temp_c"),
            "care_soil": trefle_care.get("soil"),
            "from_cache": from_cache,
        }
    except Exception:
        # Last-resort safety net (not the primary error-handling mechanism —
        # each source client already fails soft). Never hard-error on a
        # candidate the user already has in hand.
        return {
            "scientific_name": scientific_name,
            "gbif_usage_key": None,
            "family": None,
            "genus": scientific_name.split(" ")[0] if scientific_name else None,
            "common_name": fallback_common_name,
            "common_name_source": "plantnet_fallback" if fallback_common_name else None,
            "description": None,
            "description_source": None,
            "photos": [],
            "care_light": None,
            "care_humidity": None,
            "care_min_temp_c": None,
            "care_max_temp_c": None,
            "care_soil": None,
            "from_cache": False,
        }
