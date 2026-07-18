#!/usr/bin/env python3
"""Standalone smoke test for the Pl@ntNet client, isolated from the API/DB.

Usage:
    python scripts/test_plantnet.py <path-to-photo.jpg> [--disease | --variety [--species=<name>]]
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import plantnet_client  # noqa: E402


def main():
    flags = [a for a in sys.argv[1:] if a.startswith("--")]
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    disease = "--disease" in flags
    variety = "--variety" in flags
    species = next((f.split("=", 1)[1] for f in flags if f.startswith("--species=")), None)

    if len(args) != 1:
        print(
            "Usage: test_plantnet.py <path-to-photo.jpg> [--disease | --variety [--species=<name>]]",
            file=sys.stderr,
        )
        sys.exit(1)

    image_bytes = Path(args[0]).read_bytes()
    if disease:
        candidates, raw = plantnet_client.identify_disease(image_bytes)
        for c in candidates:
            print(f"{c.probability:.2%}  {c.name}  ({c.description})")
    elif variety:
        candidates, raw = plantnet_client.identify_variety(image_bytes, expected_species=species)
        for c in candidates:
            print(f"{c.probability:.2%}  {c.name}")
    else:
        candidates, raw = plantnet_client.identify_species(image_bytes)
        for c in candidates:
            print(f"{c.probability:.2%}  {c.scientific_name}  ({', '.join(c.common_names)})")

    print(f"\nremaining requests today: {raw.get('remainingIdentificationRequests')}")
    print("\n--- raw response ---")
    print(json.dumps(raw, indent=2)[:2000])


if __name__ == "__main__":
    main()
