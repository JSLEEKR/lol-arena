"""Load hand-curated ability coefficient data from data/abilities/."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from arena_sim.models.coefficients import ChampionAbilities

ABILITY_DIR = Path(__file__).resolve().parents[2] / "data" / "abilities"


@lru_cache(maxsize=1)
def load_all() -> dict[str, ChampionAbilities]:
    """Return mapping of champion_key → ChampionAbilities for every JSON in data/abilities/."""
    out: dict[str, ChampionAbilities] = {}
    if not ABILITY_DIR.exists():
        return out
    for path in sorted(ABILITY_DIR.glob("*.json")):
        try:
            raw = json.loads(path.read_text())
            ca = ChampionAbilities.model_validate(raw)
            out[ca.champion_key] = ca
        except Exception as e:  # noqa: BLE001
            raise RuntimeError(f"Failed to load ability data from {path}: {e}") from e
    return out


def get(champion_key: str) -> ChampionAbilities | None:
    return load_all().get(champion_key)


def available_keys() -> list[str]:
    return sorted(load_all().keys())
