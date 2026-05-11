"""Load hand-curated ability coefficient data from data/abilities/.

Layout:
  data/abilities/<Champion>.json              # baseline (Rift)
  data/abilities/urf/<Champion>.json          # optional URF override
  data/abilities/arena/<Champion>.json        # optional Arena override

When a per-mode file exists, it takes priority for that mode. This lets us
encode mode-specific differences (e.g., Mordekaiser's R lasting longer in URF,
or champion-specific Arena prismatic effects) without forking the schema.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from arena_sim.models.coefficients import ChampionAbilities

ABILITY_DIR = Path(__file__).resolve().parents[2] / "data" / "abilities"

# Subdirectories searched for per-mode overrides. Must match GameModeKey values.
MODE_SUBDIRS = ("rift", "arena", "urf")


def _load_from_dir(dir_path: Path) -> dict[str, ChampionAbilities]:
    out: dict[str, ChampionAbilities] = {}
    if not dir_path.exists() or not dir_path.is_dir():
        return out
    for path in sorted(dir_path.glob("*.json")):
        try:
            raw = json.loads(path.read_text())
            ca = ChampionAbilities.model_validate(raw)
            out[ca.champion_key] = ca
        except Exception as e:  # noqa: BLE001
            raise RuntimeError(f"Failed to load ability data from {path}: {e}") from e
    return out


@lru_cache(maxsize=1)
def _all() -> dict[str | None, dict[str, ChampionAbilities]]:
    """Internal: load baseline + every mode override directory once.

    Returns dict keyed by mode_key (or None for baseline).
    """
    baseline = _load_from_dir(ABILITY_DIR)
    result: dict[str | None, dict[str, ChampionAbilities]] = {None: baseline}
    for sub in MODE_SUBDIRS:
        result[sub] = _load_from_dir(ABILITY_DIR / sub)
    return result


def load_all() -> dict[str, ChampionAbilities]:
    """Backwards-compatible: return the baseline ability map."""
    return _all()[None]


def get(champion_key: str, mode_key: str | None = None) -> ChampionAbilities | None:
    """Return ability data, preferring a mode override if present."""
    all_data = _all()
    if mode_key and (override := all_data.get(mode_key, {}).get(champion_key)):
        return override
    return all_data[None].get(champion_key)


def available_keys() -> list[str]:
    return sorted(_all()[None].keys())
