import uuid
from datetime import UTC, date, datetime

from sqlmodel import Field, Relationship, SQLModel


def new_id() -> str:
    return uuid.uuid4().hex[:12]


class PlantTagLink(SQLModel, table=True):
    __tablename__ = "plant_tags"

    plant_id: str = Field(foreign_key="plants.id", primary_key=True)
    tag_id: int | None = Field(default=None, foreign_key="tags.id", primary_key=True)


class Tag(SQLModel, table=True):
    __tablename__ = "tags"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)

    plants: list["Plant"] = Relationship(back_populates="tags", link_model=PlantTagLink)


class PlantPhoto(SQLModel, table=True):
    __tablename__ = "plant_photos"

    id: str = Field(default_factory=new_id, primary_key=True)
    plant_id: str = Field(foreign_key="plants.id", index=True)
    filename: str
    is_primary: bool = False
    taken_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    vault_attachment_path: str | None = None

    plant: "Plant" = Relationship(back_populates="photos")


class SpeciesEnrichment(SQLModel, table=True):
    __tablename__ = "species_enrichments"

    scientific_name: str = Field(primary_key=True)  # GBIF canonical name, lowercased
    gbif_usage_key: int | None = None
    raw_data: str  # JSON blob: vernacular_names[], inaturalist_taxon, wikipedia_summary, trefle_care
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Plant(SQLModel, table=True):
    __tablename__ = "plants"

    id: str = Field(default_factory=new_id, primary_key=True)

    species_scientific: str | None = None
    common_name: str | None = None
    id_confidence: float | None = None
    id_source: str | None = None  # "plantnet" | "manual"
    variety: str | None = None
    id_raw_response: str | None = None  # JSON blob, audit trail

    collection: str | None = Field(default=None, index=True)
    quantity: int = 1
    for_sale: bool = False
    price_cents: int | None = None

    date_added: date = Field(default_factory=date.today)
    date_identified: date | None = None

    care_light: str | None = None
    care_water: str | None = None
    care_soil: str | None = None
    care_temperature: str | None = None
    care_humidity: str | None = None
    care_fertilizer: str | None = None
    care_notes_extra: str | None = None

    user_notes: str | None = None

    vault_note_path: str | None = None
    vault_synced_at: datetime | None = None

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    photos: list[PlantPhoto] = Relationship(back_populates="plant")
    tags: list[Tag] = Relationship(back_populates="plants", link_model=PlantTagLink)
