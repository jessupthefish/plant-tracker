"""Generates structured plant-care instructions via the Claude API."""

import json

from anthropic import APIError, Anthropic

from app.config import settings

MODEL = "claude-sonnet-5"

CARE_FIELDS = ["light", "water", "soil", "temperature", "humidity", "fertilizer"]

# notes_extra is requested and returned, but isn't required for a response to be
# considered complete, so it stays out of CARE_FIELDS.
_ALL_FIELDS = CARE_FIELDS + ["notes_extra"]

# Structured outputs constrain the decoder, so the response is always a valid
# JSON object with exactly these keys. This replaces asking for JSON in the
# system prompt and then parsing whatever came back: the model used to wrap its
# object in a ```json fence, which failed a strict json.loads().
#
# Note: assistant prefill (seeding the reply with "{") is NOT an alternative —
# it returns a 400 on Sonnet 4.6 and every later model.
CARE_SCHEMA = {
    "type": "object",
    "properties": {f: {"type": "string"} for f in _ALL_FIELDS},
    "required": _ALL_FIELDS,
    "additionalProperties": False,
}

SYSTEM_PROMPT = """You are a horticulture reference assistant. Given a plant's \
scientific (and optionally common) name, produce concise, practical care \
instructions for a home grower.

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
            output_config={"format": {"type": "json_schema", "schema": CARE_SCHEMA}},
            messages=[{"role": "user", "content": f"Plant: {subject}"}],
        )
    except APIError as exc:
        raise CareGenerationError(f"Claude API request failed: {exc}") from exc

    if message.stop_reason == "max_tokens":
        raise CareGenerationError(
            "Claude hit the output token limit before finishing; the JSON is truncated. "
            "Raise max_tokens and retry."
        )

    text = "".join(block.text for block in message.content if block.type == "text").strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise CareGenerationError(f"Claude did not return valid JSON: {text!r}") from exc

    missing = [f for f in CARE_FIELDS if f not in data]
    if missing:
        raise CareGenerationError(f"Claude response missing fields {missing}: {data!r}")

    return data
