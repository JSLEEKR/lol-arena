"""Item scraper using Data Dragon.

DDragon item shape:
    data.<id>.name, .description, .gold.total, .stats: {FlatHPPoolMod: 100, ...},
    .tags: ["HealthRegen", ...]
Stats dict uses internal flag names. We map a subset to our ItemStats fields.
Items not in Arena typically still appear; arena-prismatic items live in the
CommunityDragon arena.json (handled separately).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from arena_sim.data.client import CDragonClient
from arena_sim.data.sources import DDRAGON_VERSIONS, ddragon_items
from arena_sim.models.item import Item, ItemStats

log = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"

# Map DDragon's FlatXMod / PercentXMod keys → our ItemStats fields.
# Percent values come in as fractions (0..1); flats are absolute numbers.
_STAT_MAP: dict[str, str] = {
    "FlatHPPoolMod": "hp",
    "FlatMPPoolMod": "mp",
    "FlatArmorMod": "armor",
    "FlatSpellBlockMod": "mr",
    "FlatPhysicalDamageMod": "attack_damage",
    "FlatMagicDamageMod": "ability_power",
    "FlatMovementSpeedMod": "movespeed_flat",
    "PercentMovementSpeedMod": "movespeed_pct",
    "PercentAttackSpeedMod": "attack_speed_pct",
    "FlatCritChanceMod": "crit_chance",
    "PercentLifeStealMod": "lifesteal",
    "FlatHPRegenMod": "hp",  # weak proxy; few items grant flat regen this way
}


def _parse_stats(raw_stats: dict[str, float]) -> ItemStats:
    out: dict[str, float] = {}
    for k, v in raw_stats.items():
        field = _STAT_MAP.get(k)
        if field is not None:
            out[field] = out.get(field, 0.0) + v
    return ItemStats(**out)


def _parse_item(iid: str, raw: dict[str, Any]) -> Item | None:
    try:
        iid_int = int(iid)
    except ValueError:
        return None
    if iid_int <= 0:
        return None
    gold = raw.get("gold") or {}
    return Item(
        id=iid_int,
        name=raw.get("name", ""),
        description=raw.get("description", ""),
        cost=int(gold.get("total", 0)),
        is_arena_prismatic=False,  # DDragon doesn't flag arena items; enriched later
        is_arena_only=False,
        tags=raw.get("tags", []) or [],
        stats=_parse_stats(raw.get("stats", {}) or {}),
        raw=raw,
    )


async def scrape_all(
    client: CDragonClient | None = None,
    *,
    write: bool = True,
    version: str | None = None,
) -> list[Item]:
    owns_client = client is None
    client = client or CDragonClient()
    try:
        if version is None:
            versions = await client.get_json(DDRAGON_VERSIONS)
            version = versions[0]
        payload = await client.get_json(ddragon_items(version))
        items: list[Item] = []
        for iid, raw in (payload.get("data") or {}).items():
            try:
                it = _parse_item(iid, raw)
            except Exception as e:  # noqa: BLE001
                log.warning("Failed to parse item id=%s: %s", iid, e)
                continue
            if it is not None:
                items.append(it)
        log.info("Parsed %d items (v%s)", len(items), version)

        if write:
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            out_path = OUTPUT_DIR / "items.json"
            out_path.write_text(
                json.dumps(
                    {"version": version, "items": [i.model_dump(mode="json") for i in items]},
                    indent=2,
                )
            )
            log.info("Wrote %s", out_path)
        return items
    finally:
        if owns_client:
            await client.__aexit__(None, None, None)
