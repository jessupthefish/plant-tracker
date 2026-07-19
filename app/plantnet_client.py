"""Thin wrapper around the Pl@ntNet v2 API (species + disease identification).

Kept behind this small interface so callers depend only on identify_species()
and identify_disease(), not on Pl@ntNet's request/response shape.
"""

import httpx

from app.config import settings

BASE_URL = "https://my-api.plantnet.org"
SPECIES_PROJECT = "all"  # general/all-species referential


class PlantNetError(RuntimeError):
    pass


class Candidate:
    def __init__(self, scientific_name: str, common_name: str | None, probability: float):
        self.scientific_name = scientific_name
        self.common_name = common_name
        self.probability = probability

    def to_dict(self) -> dict:
        return {
            "scientific_name": self.scientific_name,
            "common_name": self.common_name,
            "probability": self.probability,
        }


class DiseaseCandidate:
    def __init__(self, name: str, probability: float, description: str | None = None):
        self.name = name
        self.description = description
        self.probability = probability

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "probability": self.probability,
        }


def _post(
    path: str,
    image_bytes: bytes,
    *,
    nb_results: int,
    lang: str | None = None,
    treat_as_empty: frozenset[int] = frozenset(),
) -> dict:
    """POSTs an image to Pl@ntNet. Status codes in `treat_as_empty` come back
    as {} rather than raising, for endpoints where "no match" is signalled
    via an error status instead of a 200 with an empty results list.
    """
    if not settings.plantnet_api_key:
        raise PlantNetError("PLANTNET_API_KEY is not set in .env")

    files = {"images": ("photo.jpg", image_bytes, "image/jpeg")}
    params = {"api-key": settings.plantnet_api_key, "nb-results": nb_results}
    if lang:
        params["lang"] = lang

    response = httpx.post(f"{BASE_URL}{path}", files=files, params=params, timeout=30.0)
    if response.status_code in treat_as_empty:
        return {}
    if response.status_code >= 400:
        raise PlantNetError(f"Pl@ntNet API error {response.status_code}: {response.text}")
    return response.json()


def _pick_common_name(common_names: list[str]) -> str | None:
    """Picks one deterministic common name from Pl@ntNet's commonNames list.

    With lang="en" requested, Pl@ntNet already returns English-only names
    ordered by relevance, so the first non-blank entry (after trimming) is
    sufficient.
    """
    for name in common_names:
        cleaned = name.strip()
        if cleaned:
            return cleaned
    return None


def identify_species(image_bytes: bytes, top_n: int = 5) -> tuple[list[Candidate], dict]:
    """Returns (candidates sorted by probability desc, raw API response)."""
    raw = _post(f"/v2/identify/{SPECIES_PROJECT}", image_bytes, nb_results=top_n, lang="en")
    try:
        results = raw["results"]
    except (KeyError, TypeError) as exc:
        raise PlantNetError(f"Unexpected Pl@ntNet response shape: {raw}") from exc

    candidates = [
        Candidate(
            scientific_name=r["species"].get("scientificNameWithoutAuthor", "Unknown"),
            common_name=_pick_common_name(r["species"].get("commonNames") or []),
            probability=r.get("score", 0.0),
        )
        for r in results[:top_n]
    ]
    candidates.sort(key=lambda c: c.probability, reverse=True)
    return candidates, raw


def identify_disease(image_bytes: bytes, top_n: int = 5) -> tuple[list[DiseaseCandidate], dict]:
    """Returns (candidates sorted by probability desc, raw API response).

    Pl@ntNet's disease coverage is limited to a specific list of species and
    pathologies, so an empty candidate list is a normal (non-error) outcome.
    """
    raw = _post("/v2/diseases/identify", image_bytes, nb_results=top_n)
    try:
        results = raw["results"]
    except (KeyError, TypeError) as exc:
        raise PlantNetError(f"Unexpected Pl@ntNet response shape: {raw}") from exc

    candidates = [
        DiseaseCandidate(
            name=r.get("name", "Unknown"),
            description=r.get("description"),
            probability=r.get("score", 0.0),
        )
        for r in results[:top_n]
    ]
    candidates.sort(key=lambda c: c.probability, reverse=True)
    return candidates, raw


class VarietyCandidate:
    def __init__(self, name: str, probability: float):
        self.name = name
        self.probability = probability

    def to_dict(self) -> dict:
        return {"name": self.name, "probability": self.probability}


def identify_variety(
    image_bytes: bytes, expected_species: str | None = None, top_n: int = 5
) -> tuple[list[VarietyCandidate], dict]:
    """Returns (candidates sorted by probability desc, raw API response).

    /v2/varieties/identify returns a list of species results, each bundling
    its own varieties[]. We pick the result entry matching expected_species
    (case-insensitive, on scientificNameWithoutAuthor), falling back to the
    top-scored entry if there's no match or no expected_species was given,
    then flatten that entry's varieties[]. Pl@ntNet's variety coverage is
    limited to a specific list of (mostly agricultural/ornamental) species —
    for anything outside that list it responds with a 404 "Species not
    found" rather than a 200 with empty results, so that status is treated
    as a normal empty-candidates outcome here, not an error.
    """
    raw = _post("/v2/varieties/identify", image_bytes, nb_results=top_n, treat_as_empty=frozenset({404}))
    if not raw:
        return [], raw
    try:
        results = raw["results"]
    except (KeyError, TypeError) as exc:
        raise PlantNetError(f"Unexpected Pl@ntNet response shape: {raw}") from exc

    if not results:
        return [], raw

    chosen = results[0]
    if expected_species:
        needle = expected_species.strip().lower()
        for r in results:
            name = r.get("species", {}).get("scientificNameWithoutAuthor", "")
            if name.strip().lower() == needle:
                chosen = r
                break

    varieties = chosen.get("varieties") or []
    candidates = [
        VarietyCandidate(name=v.get("name", "Unknown"), probability=v.get("score", 0.0))
        for v in varieties[:top_n]
    ]
    candidates.sort(key=lambda c: c.probability, reverse=True)
    return candidates, raw
