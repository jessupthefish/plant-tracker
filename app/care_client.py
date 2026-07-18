"""Generates structured plant-care instructions via the Claude API."""

import json

from anthropic import APIError, Anthropic

from app.config import settings

MODEL = "claude-sonnet-5"

CARE_FIELDS = ["light", "water", "soil", "temperature", "humidity", "fertilizer"]

SYSTEM_PROMPT = """You are a horticulture reference assistant. Given a plant's \
scientific (and optionally common) name, produce concise, practical care \
instructions for a home grower.

Respond with ONLY a JSON object, no prose before or after, with exactly these \
string keys: light, water, soil, temperature, humidity, fertilizer, notes_extra. \
Each value should be one or two short sentences. "notes_extra" is for any \
noteworthy care detail that doesn't fit the other fields (e.g. toxicity to pets, \
common pests, dormancy behavior) — leave it as an empty string if there's nothing \
to add."""


class CareGenerationError(RuntimeError):
    pass


def generate_care_instructions(species_scientific: str, common_name: str | None = None) -> dict:
    if not settings.anthropic_api_key:
        raise CareGenerationError("ANTHROPIC_API_KEY is not set in .env")

    client = Anthropic(api_key=settings.anthropic_api_key)
    subject = species_scientific
    if common_name:
        subject += f" ({common_name})"

    try:
        message = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": f"Plant: {subject}"}],
        )
    except APIError as exc:
        raise CareGenerationError(f"Claude API request failed: {exc}") from exc

    text = "".join(block.text for block in message.content if block.type == "text").strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise CareGenerationError(f"Claude did not return valid JSON: {text!r}") from exc

    missing = [f for f in CARE_FIELDS if f not in data]
    if missing:
        raise CareGenerationError(f"Claude response missing fields {missing}: {data!r}")

    return data
