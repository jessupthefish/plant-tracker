"""Pushes a fully-derived view of the plant catalog into the Obsidian vault.

The database is the source of truth. Notes written here are always fully
regenerated/overwritten — never hand-edited in the vault. When
VAULT_SSH_HOST == "local" (dev), files are written directly to
VAULT_LOCAL_PATH. Otherwise they're rsync'd over SSH to VAULT_SSH_HOST at
VAULT_REMOTE_PATH (the your-server -> Mac production path).
"""

import re
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from sqlmodel import Session

from app.config import settings
from app.models import Plant

NOTES_SUBDIR = "Life/Plants"
ATTACHMENTS_SUBDIR = "Attachments/Plants"
ARCHIVE_SUBDIR = "Archive/Plants"

CARE_LABELS = [
    ("care_light", "Light"),
    ("care_water", "Water"),
    ("care_soil", "Soil"),
    ("care_temperature", "Temperature"),
    ("care_humidity", "Humidity"),
    ("care_fertilizer", "Fertilizer"),
]


def slugify(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower())
    return re.sub(r"-+", "-", value).strip("-") or "plant"


def _yaml_str(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _genus(species_scientific: str | None) -> str | None:
    if not species_scientific:
        return None
    return species_scientific.strip().split(" ")[0] or None


def render_note(plant: Plant) -> str:
    name_for_file = plant.common_name or plant.species_scientific or "Unknown plant"
    tags = " ".join(f"\n  - {t.name}" for t in plant.tags)
    tags_line = f"[{', '.join(t.name for t in plant.tags)}]" if plant.tags else "[]"

    frontmatter = "\n".join(
        [
            "---",
            "type: plant",
            f"plant_id: {plant.id}",
            f"species: {_yaml_str(plant.species_scientific)}",
            f"genus: {_yaml_str(_genus(plant.species_scientific))}",
            f"common_name: {_yaml_str(plant.common_name)}",
            f"collection: {_yaml_str(plant.collection)}",
            f"tags: {tags_line}",
            f"quantity: {plant.quantity}",
            f"for_sale: {_yaml_str(plant.for_sale)}",
            f"price: {plant.price_cents / 100 if plant.price_cents else ''}",
            f"date_added: {_yaml_str(plant.date_added)}",
            f"date_identified: {_yaml_str(plant.date_identified)}",
            f"id_confidence: {_yaml_str(plant.id_confidence)}",
            f"id_source: {_yaml_str(plant.id_source)}",
            f"variety: {_yaml_str(plant.variety)}",
            "---",
        ]
    )

    title = name_for_file
    subtitle = (
        f" ({plant.species_scientific})"
        if plant.species_scientific and plant.species_scientific != name_for_file
        else ""
    )

    lines = [
        frontmatter,
        "",
        f"# {title}{subtitle}",
        "",
        "> [!info] This note is fully derived from the Plant Tracker database. "
        "Do not hand-edit — changes will be overwritten on the next sync. "
        "Edit via the Plant Tracker app instead.",
        "",
    ]

    primary_photo = next((p for p in plant.photos if p.is_primary), None) or (
        plant.photos[0] if plant.photos else None
    )
    other_photos = [p for p in plant.photos if p is not primary_photo]
    ordered_photos = ([primary_photo] if primary_photo else []) + other_photos
    for photo in ordered_photos:
        if photo.vault_attachment_path:
            lines.append(f"![[{Path(photo.vault_attachment_path).name}]]")
    if ordered_photos:
        lines.append("")

    lines.append("## Care")
    for field, label in CARE_LABELS:
        value = getattr(plant, field)
        if value:
            lines.append(f"- **{label}:** {value}")
    if plant.care_notes_extra:
        lines.append(f"- **Other:** {plant.care_notes_extra}")
    lines.append("")

    lines.append("## Notes")
    lines.append(plant.user_notes or "*(none)*")
    lines.append("")

    lines.append("---")
    lines.append(f"*Last synced: {datetime.now().strftime('%Y-%m-%d %H:%M')}*")

    return "\n".join(lines) + "\n"


def note_filename(plant: Plant) -> str:
    name = plant.common_name or plant.species_scientific or "plant"
    return f"{slugify(name)}-{plant.id}.md"


def _local_root() -> Path:
    return settings.vault_local_path


def _write_local(relative_path: str, content: str | bytes) -> None:
    dest = _local_root() / relative_path
    dest.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        dest.write_bytes(content)
    else:
        dest.write_text(content)


def _move_local(relative_src: str, relative_dst: str) -> None:
    src = _local_root() / relative_src
    if not src.exists():
        return
    dst = _local_root() / relative_dst
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))


def _push_remote(staging_dir: Path) -> None:
    host = settings.vault_ssh_host
    remote_path = settings.vault_remote_path
    subprocess.run(["ssh", host, f"mkdir -p '{remote_path}'"], check=True)
    subprocess.run(
        ["rsync", "-avz", f"{staging_dir}/", f"{host}:{remote_path}/"],
        check=True,
    )


def sync_plant(session: Session, plant: Plant) -> None:
    """Renders and pushes/writes one plant's note + photos, then updates sync bookkeeping."""
    note_name = note_filename(plant)
    note_rel_path = f"{NOTES_SUBDIR}/{note_name}"

    for photo in plant.photos:
        photo.vault_attachment_path = (
            f"{ATTACHMENTS_SUBDIR}/{slugify(plant.common_name or plant.species_scientific or 'plant')}"
            f"-{plant.id}-{photo.id}{Path(photo.filename).suffix}"
        )

    note_content = render_note(plant)

    if settings.vault_ssh_host == "local":
        _write_local(note_rel_path, note_content)
        for photo in plant.photos:
            src = settings.photos_dir / plant.id / photo.filename
            if src.exists():
                _write_local(photo.vault_attachment_path, src.read_bytes())
    else:
        staging = settings.photos_dir / "_vault_staging" / plant.id
        (staging / NOTES_SUBDIR).mkdir(parents=True, exist_ok=True)
        (staging / ATTACHMENTS_SUBDIR).mkdir(parents=True, exist_ok=True)
        (staging / note_rel_path).write_text(note_content)
        for photo in plant.photos:
            src = settings.photos_dir / plant.id / photo.filename
            if src.exists():
                shutil.copy(src, staging / photo.vault_attachment_path)
        _push_remote(staging)
        shutil.rmtree(staging, ignore_errors=True)

    plant.vault_note_path = note_rel_path
    plant.vault_synced_at = datetime.now(UTC)
    session.add(plant)
    session.commit()


def archive_plant(plant_id: str, note_path: str | None) -> None:
    """Moves a deleted plant's note/photos into Archive/Plants instead of deleting them."""
    if not note_path:
        return
    note_name = Path(note_path).name
    archive_rel = f"{ARCHIVE_SUBDIR}/{note_name}"

    if settings.vault_ssh_host == "local":
        _move_local(note_path, archive_rel)
    else:
        remote_path = settings.vault_remote_path
        subprocess.run(
            ["ssh", settings.vault_ssh_host, f"mkdir -p '{remote_path}/{ARCHIVE_SUBDIR}'"],
            check=True,
        )
        subprocess.run(
            [
                "ssh",
                settings.vault_ssh_host,
                f"mv '{remote_path}/{note_path}' '{remote_path}/{archive_rel}' 2>/dev/null || true",
            ],
            check=False,
        )
