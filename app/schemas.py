from datetime import date, datetime

from pydantic import BaseModel


class CandidateOut(BaseModel):
    scientific_name: str
    common_name: str | None
    probability: float


class IdentifyResponse(BaseModel):
    candidates: list[CandidateOut]


class DiseaseCandidateOut(BaseModel):
    name: str
    description: str | None = None
    probability: float


class DiseaseResponse(BaseModel):
    candidates: list[DiseaseCandidateOut]


class VarietyCandidateOut(BaseModel):
    name: str
    probability: float


class VarietyResponse(BaseModel):
    candidates: list[VarietyCandidateOut]


class EnrichedPhotoOut(BaseModel):
    url: str
    source: str  # "inaturalist" | "wikipedia"
    attribution: str | None = None
    license_code: str | None = None


class SpeciesEnrichmentOut(BaseModel):
    scientific_name: str
    gbif_usage_key: int | None = None
    family: str | None = None
    genus: str | None = None
    common_name: str | None = None
    common_name_source: str | None = None  # "catalog" | "inaturalist" | "gbif_vernacular" | "plantnet_fallback" | None
    description: str | None = None
    description_source: str | None = None  # "wikipedia" | None
    photos: list[EnrichedPhotoOut] = []
    care_light: str | None = None
    care_humidity: str | None = None
    care_min_temp_c: float | None = None
    care_max_temp_c: float | None = None
    care_soil: str | None = None
    from_cache: bool = False


class PhotoOut(BaseModel):
    id: str
    filename: str
    is_primary: bool
    vault_attachment_path: str | None = None


class PlantOut(BaseModel):
    id: str
    species_scientific: str | None
    genus: str | None
    common_name: str | None
    id_confidence: float | None
    id_source: str | None
    variety: str | None
    collection: str | None
    quantity: int
    for_sale: bool
    price_cents: int | None
    date_added: date
    date_identified: date | None
    care_light: str | None
    care_water: str | None
    care_soil: str | None
    care_temperature: str | None
    care_humidity: str | None
    care_fertilizer: str | None
    care_notes_extra: str | None
    user_notes: str | None
    tags: list[str]
    photos: list[PhotoOut]
    vault_note_path: str | None
    vault_synced_at: datetime | None
    created_at: datetime
    updated_at: datetime


class PlantUpdate(BaseModel):
    species_scientific: str | None = None
    common_name: str | None = None
    variety: str | None = None
    collection: str | None = None
    quantity: int | None = None
    for_sale: bool | None = None
    price_cents: int | None = None
    user_notes: str | None = None
    tags: list[str] | None = None
    care_light: str | None = None
    care_water: str | None = None
    care_soil: str | None = None
    care_temperature: str | None = None
    care_humidity: str | None = None
    care_fertilizer: str | None = None
    care_notes_extra: str | None = None
