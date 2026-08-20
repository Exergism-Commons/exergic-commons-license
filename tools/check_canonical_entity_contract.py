#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import canonical_dossier_contract as contract

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    errors = contract.validate(ROOT)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print(f"canonical dossier contract: FAILED ({len(errors)} error(s))")
        return 1
    print("canonical dossier contract: OK (universe binding, canonical visual paths, raster facsimiles, SVG clipping)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
