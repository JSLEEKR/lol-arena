"""Generate ability JSON skeletons for every champion missing a curated file.

For each champion in data/processed/champions.json that doesn't already have a
data/abilities/<key>.json, write a skeleton with:
  - real cooldowns, names, and max ranks (from DDragon spell data)
  - empty hits[] (damage formulas need manual curation)
  - verified: false

The runtime treats empty hits as "no ability damage data" — auto-only DPS
remains accurate, and the CLI surfaces a warning when the file is unverified.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from arena_sim.models import Champion

ROOT = Path(__file__).resolve().parents[1]
CHAMPIONS_FILE = ROOT / "data" / "processed" / "champions.json"
ABILITIES_DIR = ROOT / "data" / "abilities"


def main() -> int:
    if not CHAMPIONS_FILE.exists():
        print("Run `arena scrape champions` first.", file=sys.stderr)
        return 2

    blob = json.loads(CHAMPIONS_FILE.read_text())
    champs = [Champion.model_validate(c) for c in blob.get("champions", [])]

    existing = {p.stem for p in ABILITIES_DIR.glob("*.json")}
    written = 0
    for c in champs:
        if c.key in existing:
            continue
        out: dict = {"champion_key": c.key, "abilities": {}, "verified": False}
        for ab in c.abilities:
            if ab.slot.value == "P":
                continue
            out["abilities"][ab.slot.value] = {
                "slot": ab.slot.value,
                "name": ab.name,
                "cooldown": list(ab.cooldown),
                "cast_time": 0.25,
                "hits": [],
            }
        target = ABILITIES_DIR / f"{c.key}.json"
        target.write_text(json.dumps(out, indent=2) + "\n")
        written += 1
    print(f"Wrote {written} skeleton ability files to {ABILITIES_DIR}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
