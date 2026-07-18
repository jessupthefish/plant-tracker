#!/usr/bin/env python3
"""Standalone smoke test for the Claude care-instructions client.

Usage: python scripts/test_care.py "Monstera deliciosa" ["Swiss Cheese Plant"]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import care_client  # noqa: E402


def main():
    if len(sys.argv) not in (2, 3):
        print('Usage: test_care.py "<species>" ["<common name>"]', file=sys.stderr)
        sys.exit(1)

    species = sys.argv[1]
    common_name = sys.argv[2] if len(sys.argv) == 3 else None
    care = care_client.generate_care_instructions(species, common_name)

    for field, value in care.items():
        print(f"{field}: {value}")


if __name__ == "__main__":
    main()
