from contextlib import asynccontextmanager
from datetime import UTC, date, datetime

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlmodel import Session, select

from app import care_client, plantnet_client, species_enrichment, vault_sync
from app.config import settings
from app.db import get_session, init_db
from app.models import Plant, PlantPhoto, Tag
from app.schemas import (
    CandidateOut,
    DiseaseCandidateOut,
    DiseaseResponse,
    IdentifyResponse,
    PhotoOut,
    PlantOut,
    PlantUpdate,
    SpeciesEnrichmentOut,
    VarietyCandidateOut,
    VarietyResponse,
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title="NOIDChonk", lifespan=lifespan)


def require_auth(authorization: str | None = Header(default=None)) -> None:
    if not settings.api_bearer_token:
        return  # no token configured -> auth disabled (local dev)
    expected = f"Bearer {settings.api_bearer_token}"
    if authorization != expected:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or missing bearer token")


def _genus(species_scientific: str | None) -> str | None:
    if not species_scientific:
        return None
    return species_scientific.strip().split(" ")[0] or None


_SORT_KEYS = {
    "name": lambda p: (p.common_name or p.species_scientific or "").lower(),
    "date_added": lambda p: p.date_added,
    "quantity": lambda p: p.quantity,
}


def _sort_plants(plants: list[Plant], sort: str | None) -> list[Plant]:
    sort = sort or "-date_added"
    reverse = sort.startswith("-")
    key = sort[1:] if reverse else sort
    key_fn = _SORT_KEYS.get(key, _SORT_KEYS["date_added"])
    return sorted(plants, key=key_fn, reverse=reverse)


def _plant_out(plant: Plant) -> PlantOut:
    return PlantOut(
        id=plant.id,
        species_scientific=plant.species_scientific,
        genus=_genus(plant.species_scientific),
        common_name=plant.common_name,
        id_confidence=plant.id_confidence,
        id_source=plant.id_source,
        variety=plant.variety,
        collection=plant.collection,
        quantity=plant.quantity,
        for_sale=plant.for_sale,
        price_cents=plant.price_cents,
        date_added=plant.date_added,
        date_identified=plant.date_identified,
        care_light=plant.care_light,
        care_water=plant.care_water,
        care_soil=plant.care_soil,
        care_temperature=plant.care_temperature,
        care_humidity=plant.care_humidity,
        care_fertilizer=plant.care_fertilizer,
        care_notes_extra=plant.care_notes_extra,
        user_notes=plant.user_notes,
        tags=[t.name for t in plant.tags],
        photos=[
            PhotoOut(
                id=p.id, filename=p.filename, is_primary=p.is_primary,
                vault_attachment_path=p.vault_attachment_path,
            )
            for p in plant.photos
        ],
        vault_note_path=plant.vault_note_path,
        vault_synced_at=plant.vault_synced_at,
        created_at=plant.created_at,
        updated_at=plant.updated_at,
    )


def _get_or_create_tags(session: Session, names: list[str]) -> list[Tag]:
    tags = []
    for raw in names:
        name = raw.strip().lower()
        if not name:
            continue
        tag = session.exec(select(Tag).where(Tag.name == name)).first()
        if not tag:
            tag = Tag(name=name)
            session.add(tag)
            session.commit()
            session.refresh(tag)
        tags.append(tag)
    return tags


def _save_photo(session: Session, plant: Plant, upload_bytes: bytes, filename: str) -> PlantPhoto:
    plant_dir = settings.photos_dir / plant.id
    plant_dir.mkdir(parents=True, exist_ok=True)
    dest_name = f"{len(plant.photos) + 1}_{filename}"
    (plant_dir / dest_name).write_bytes(upload_bytes)
    photo = PlantPhoto(
        plant_id=plant.id, filename=dest_name, is_primary=(len(plant.photos) == 0)
    )
    session.add(photo)
    session.commit()
    session.refresh(photo)
    return photo


@app.get("/api/v1/health")
def health():
    return {"status": "ok"}


@app.post("/api/v1/identify", response_model=IdentifyResponse, dependencies=[Depends(require_auth)])
async def identify(photo: UploadFile = File(...)):
    image_bytes = await photo.read()
    try:
        candidates, _raw = plantnet_client.identify_species(image_bytes)
    except plantnet_client.PlantNetError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
    return IdentifyResponse(
        candidates=[
            CandidateOut(
                scientific_name=c.scientific_name,
                common_name=c.common_name,
                probability=c.probability,
            )
            for c in candidates
        ]
    )


@app.post("/api/v1/check-health", response_model=DiseaseResponse, dependencies=[Depends(require_auth)])
async def check_health(photo: UploadFile = File(...)):
    image_bytes = await photo.read()
    try:
        candidates, _raw = plantnet_client.identify_disease(image_bytes)
    except plantnet_client.PlantNetError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
    return DiseaseResponse(
        candidates=[
            DiseaseCandidateOut(
                name=c.name,
                description=c.description,
                probability=c.probability,
            )
            for c in candidates
        ]
    )


@app.post("/api/v1/identify-variety", response_model=VarietyResponse, dependencies=[Depends(require_auth)])
async def identify_variety(
    photo: UploadFile = File(...),
    species: str | None = Form(default=None),
):
    image_bytes = await photo.read()
    try:
        candidates, _raw = plantnet_client.identify_variety(image_bytes, expected_species=species)
    except plantnet_client.PlantNetError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
    return VarietyResponse(
        candidates=[
            VarietyCandidateOut(name=c.name, probability=c.probability) for c in candidates
        ]
    )


@app.get("/api/v1/species/enrich", response_model=SpeciesEnrichmentOut, dependencies=[Depends(require_auth)])
async def enrich_species_route(
    scientific_name: str,
    common_name: str | None = None,
    locale: str | None = None,
    country: str | None = None,
    session: Session = Depends(get_session),
):
    result = await species_enrichment.enrich_species(
        session=session,
        scientific_name=scientific_name,
        locale=locale,
        country=country,
        fallback_common_name=common_name,
    )
    return SpeciesEnrichmentOut(**result)


@app.post("/api/v1/plants", response_model=PlantOut, dependencies=[Depends(require_auth)])
async def create_plant(
    species_scientific: str | None = Form(default=None),
    common_name: str | None = Form(default=None),
    variety: str | None = Form(default=None),
    collection: str | None = Form(default=None),
    tags: str = Form(default=""),
    quantity: int = Form(default=1),
    for_sale: bool = Form(default=False),
    price_cents: int | None = Form(default=None),
    user_notes: str | None = Form(default=None),
    id_confidence: float | None = Form(default=None),
    id_source: str | None = Form(default=None),
    photo: UploadFile | None = File(default=None),
    session: Session = Depends(get_session),
):
    plant = Plant(
        species_scientific=species_scientific,
        common_name=common_name,
        variety=variety,
        collection=collection,
        quantity=quantity,
        for_sale=for_sale,
        price_cents=price_cents,
        user_notes=user_notes,
        id_confidence=id_confidence,
        id_source=id_source,
        date_identified=date.today() if species_scientific else None,
    )
    tag_names = [t for t in tags.split(",") if t.strip()]
    plant.tags = _get_or_create_tags(session, tag_names)
    session.add(plant)
    session.commit()
    session.refresh(plant)

    if photo is not None:
        image_bytes = await photo.read()
        _save_photo(session, plant, image_bytes, photo.filename or "photo.jpg")
        session.refresh(plant)

    if species_scientific:
        try:
            care = care_client.generate_care_instructions(species_scientific, common_name)
            plant.care_light = care["light"]
            plant.care_water = care["water"]
            plant.care_soil = care["soil"]
            plant.care_temperature = care["temperature"]
            plant.care_humidity = care["humidity"]
            plant.care_fertilizer = care["fertilizer"]
            plant.care_notes_extra = care.get("notes_extra") or None
        except care_client.CareGenerationError:
            pass  # leave care fields blank; user can retry via /regenerate-care
        session.add(plant)
        session.commit()
        session.refresh(plant)

    vault_sync.sync_plant(session, plant)
    session.refresh(plant)
    return _plant_out(plant)


@app.get("/api/v1/plants", response_model=list[PlantOut], dependencies=[Depends(require_auth)])
def list_plants(
    collection: str | None = None,
    tag: str | None = None,
    for_sale: bool | None = None,
    genus: str | None = None,
    q: str | None = None,
    sort: str | None = None,
    session: Session = Depends(get_session),
):
    statement = select(Plant)
    if collection:
        statement = statement.where(Plant.collection == collection)
    if for_sale is not None:
        statement = statement.where(Plant.for_sale == for_sale)
    plants = session.exec(statement).all()

    if tag:
        plants = [p for p in plants if tag.lower() in [t.name for t in p.tags]]
    if genus:
        plants = [p for p in plants if _genus(p.species_scientific) == genus]
    if q:
        needle = q.lower()
        plants = [
            p
            for p in plants
            if needle in (p.species_scientific or "").lower()
            or needle in (p.common_name or "").lower()
            or needle in (p.user_notes or "").lower()
        ]
    plants = _sort_plants(plants, sort)
    return [_plant_out(p) for p in plants]


@app.get("/api/v1/plants/{plant_id}", response_model=PlantOut, dependencies=[Depends(require_auth)])
def get_plant(plant_id: str, session: Session = Depends(get_session)):
    plant = session.get(Plant, plant_id)
    if not plant:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plant not found")
    return _plant_out(plant)


@app.patch("/api/v1/plants/{plant_id}", response_model=PlantOut, dependencies=[Depends(require_auth)])
def update_plant(plant_id: str, body: PlantUpdate, session: Session = Depends(get_session)):
    plant = session.get(Plant, plant_id)
    if not plant:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plant not found")

    data = body.model_dump(exclude_unset=True, exclude={"tags"})
    for field, value in data.items():
        setattr(plant, field, value)
    if body.tags is not None:
        plant.tags = _get_or_create_tags(session, body.tags)

    plant.updated_at = datetime.now(UTC)
    session.add(plant)
    session.commit()
    session.refresh(plant)

    vault_sync.sync_plant(session, plant)
    session.refresh(plant)
    return _plant_out(plant)


@app.delete("/api/v1/plants/{plant_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_auth)])
def delete_plant(plant_id: str, session: Session = Depends(get_session)):
    plant = session.get(Plant, plant_id)
    if not plant:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plant not found")
    note_path = plant.vault_note_path
    for photo in plant.photos:
        session.delete(photo)
    session.delete(plant)
    session.commit()
    vault_sync.archive_plant(plant_id, note_path)


@app.post("/api/v1/plants/{plant_id}/photos", response_model=PhotoOut, dependencies=[Depends(require_auth)])
async def add_photo(plant_id: str, photo: UploadFile = File(...), session: Session = Depends(get_session)):
    plant = session.get(Plant, plant_id)
    if not plant:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plant not found")
    image_bytes = await photo.read()
    saved = _save_photo(session, plant, image_bytes, photo.filename or "photo.jpg")
    session.refresh(plant)
    vault_sync.sync_plant(session, plant)
    return PhotoOut(
        id=saved.id, filename=saved.filename, is_primary=saved.is_primary,
        vault_attachment_path=saved.vault_attachment_path,
    )


@app.get("/api/v1/plants/{plant_id}/photos/{photo_id}", dependencies=[Depends(require_auth)])
def get_photo(plant_id: str, photo_id: str, session: Session = Depends(get_session)):
    photo = session.get(PlantPhoto, photo_id)
    if not photo or photo.plant_id != plant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Photo not found")
    path = settings.photos_dir / plant_id / photo.filename
    if not path.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Photo file missing on disk")
    return FileResponse(path)


@app.delete(
    "/api/v1/plants/{plant_id}/photos/{photo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_auth)],
)
def delete_photo(plant_id: str, photo_id: str, session: Session = Depends(get_session)):
    plant = session.get(Plant, plant_id)
    if not plant:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plant not found")
    photo = session.get(PlantPhoto, photo_id)
    if not photo or photo.plant_id != plant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Photo not found")

    was_primary = photo.is_primary
    (settings.photos_dir / plant_id / photo.filename).unlink(missing_ok=True)
    session.delete(photo)
    session.commit()
    session.refresh(plant)

    if was_primary and plant.photos:
        plant.photos[0].is_primary = True
        session.add(plant.photos[0])
        session.commit()
        session.refresh(plant)

    vault_sync.sync_plant(session, plant)


@app.post(
    "/api/v1/plants/{plant_id}/photos/{photo_id}/set-primary",
    response_model=PlantOut,
    dependencies=[Depends(require_auth)],
)
def set_primary_photo(plant_id: str, photo_id: str, session: Session = Depends(get_session)):
    plant = session.get(Plant, plant_id)
    if not plant:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plant not found")
    if not any(p.id == photo_id for p in plant.photos):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Photo not found")

    for p in plant.photos:
        p.is_primary = p.id == photo_id
        session.add(p)
    session.commit()
    session.refresh(plant)

    vault_sync.sync_plant(session, plant)
    session.refresh(plant)
    return _plant_out(plant)


@app.post("/api/v1/plants/{plant_id}/regenerate-care", response_model=PlantOut, dependencies=[Depends(require_auth)])
def regenerate_care(plant_id: str, session: Session = Depends(get_session)):
    plant = session.get(Plant, plant_id)
    if not plant:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plant not found")
    if not plant.species_scientific:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Plant has no species set yet")
    try:
        care = care_client.generate_care_instructions(plant.species_scientific, plant.common_name)
    except care_client.CareGenerationError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
    plant.care_light = care["light"]
    plant.care_water = care["water"]
    plant.care_soil = care["soil"]
    plant.care_temperature = care["temperature"]
    plant.care_humidity = care["humidity"]
    plant.care_fertilizer = care["fertilizer"]
    plant.care_notes_extra = care.get("notes_extra") or None
    plant.updated_at = datetime.now(UTC)
    session.add(plant)
    session.commit()
    session.refresh(plant)
    vault_sync.sync_plant(session, plant)
    session.refresh(plant)
    return _plant_out(plant)


@app.post("/api/v1/plants/{plant_id}/sync", response_model=PlantOut, dependencies=[Depends(require_auth)])
def force_sync(plant_id: str, session: Session = Depends(get_session)):
    plant = session.get(Plant, plant_id)
    if not plant:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plant not found")
    vault_sync.sync_plant(session, plant)
    session.refresh(plant)
    return _plant_out(plant)


@app.get("/api/v1/tags", response_model=list[str], dependencies=[Depends(require_auth)])
def list_tags(session: Session = Depends(get_session)):
    return sorted(t.name for t in session.exec(select(Tag)).all())


@app.get("/api/v1/collections", response_model=list[str], dependencies=[Depends(require_auth)])
def list_collections(session: Session = Depends(get_session)):
    values = session.exec(select(Plant.collection).distinct()).all()
    return sorted(v for v in values if v)


@app.get("/api/v1/genera", response_model=list[str], dependencies=[Depends(require_auth)])
def list_genera(session: Session = Depends(get_session)):
    species = session.exec(select(Plant.species_scientific).distinct()).all()
    genera = {_genus(s) for s in species}
    return sorted(g for g in genera if g)
