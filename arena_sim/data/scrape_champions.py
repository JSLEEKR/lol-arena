"""Champion scraper using Riot Data Dragon.

DDragon endpoint shape (per Garen):
    data.Garen.stats: {hp, hpperlevel, mp, mpperlevel, ..., attackrange, attackspeed, attackspeedperlevel, ...}
    data.Garen.passive: {name, description, image, ...}
    data.Garen.spells: [{id, name, description, cooldown[5], cost[5], range[5], effect, leveltip, ...}]
    data.Garen.partype: "Mana" | "Energy" | "None" | ...
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from arena_sim.data.client import CDragonClient
from arena_sim.data.sources import (
    DDRAGON_VERSIONS,
    ddragon_champion_detail,
    ddragon_champion_list,
)
from arena_sim.models.champion import (
    Ability,
    AbilitySlot,
    Champion,
    ChampionStats,
    ResourceType,
)

log = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"


def _resource_from_partype(raw: str | None) -> ResourceType:
    if not raw:
        return ResourceType.NONE
    s = raw.lower().strip()
    table = {
        "mana": ResourceType.MANA,
        "energy": ResourceType.ENERGY,
        "fury": ResourceType.FURY,
        "rage": ResourceType.RAGE,
        "ferocity": ResourceType.FEROCITY,
        "heat": ResourceType.HEAT,
        "none": ResourceType.NONE,
        "no cost": ResourceType.NONE,
        "manaless": ResourceType.NONE,
        "health": ResourceType.HEALTH,
    }
    return table.get(s, ResourceType.OTHER)


def _parse_stats(s: dict[str, Any]) -> ChampionStats:
    return ChampionStats(
        hp=s.get("hp", 0),
        hp_per_level=s.get("hpperlevel", 0),
        hp_regen=s.get("hpregen", 0),
        hp_regen_per_level=s.get("hpregenperlevel", 0),
        mp=s.get("mp", 0),
        mp_per_level=s.get("mpperlevel", 0),
        mp_regen=s.get("mpregen", 0),
        mp_regen_per_level=s.get("mpregenperlevel", 0),
        armor=s.get("armor", 0),
        armor_per_level=s.get("armorperlevel", 0),
        mr=s.get("spellblock", 0),
        mr_per_level=s.get("spellblockperlevel", 0),
        attack_damage=s.get("attackdamage", 0),
        attack_damage_per_level=s.get("attackdamageperlevel", 0),
        attack_speed=s.get("attackspeed", 0.625),
        attack_speed_ratio=s.get("attackspeed", 0.625),  # DDragon ratio == base AS
        attack_speed_per_level=s.get("attackspeedperlevel", 0),
        attack_range=s.get("attackrange", 125),
        crit_base=s.get("crit", 0),
        crit_per_level=s.get("critperlevel", 0),
        movespeed=s.get("movespeed", 325),
    )


_SLOT_ORDER = [AbilitySlot.Q, AbilitySlot.W, AbilitySlot.E, AbilitySlot.R]


def _parse_abilities(detail: dict[str, Any]) -> list[Ability]:
    out: list[Ability] = []
    passive = detail.get("passive") or {}
    if passive:
        out.append(
            Ability(
                slot=AbilitySlot.PASSIVE,
                name=passive.get("name", ""),
                description=passive.get("description", ""),
                max_rank=1,
                raw=passive,
            )
        )
    for i, spell in enumerate(detail.get("spells", []) or []):
        if i >= len(_SLOT_ORDER):
            break
        slot = _SLOT_ORDER[i]
        out.append(
            Ability(
                slot=slot,
                name=spell.get("name", ""),
                description=spell.get("description", ""),
                cooldown=spell.get("cooldown") or [],
                cost=spell.get("cost") or [],
                cost_type=_resource_from_partype(spell.get("costType") or detail.get("partype")),
                range=spell.get("range") or [],
                max_rank=spell.get("maxrank", 3 if slot == AbilitySlot.R else 5),
                raw=spell,
            )
        )
    return out


def _parse_champion(detail: dict[str, Any]) -> Champion | None:
    try:
        cid = int(detail.get("key", 0))
    except (TypeError, ValueError):
        return None
    if cid <= 0:
        return None
    return Champion(
        id=cid,
        key=detail.get("id", ""),  # DDragon "id" is the alias (e.g. "Garen")
        name=detail.get("name", ""),
        title=detail.get("title", ""),
        roles=detail.get("tags", []) or [],
        resource=_resource_from_partype(detail.get("partype")),
        stats=_parse_stats(detail.get("stats", {}) or {}),
        abilities=_parse_abilities(detail),
        raw=detail,
    )


async def scrape_all(
    client: CDragonClient | None = None,
    *,
    write: bool = True,
    version: str | None = None,
) -> list[Champion]:
    owns_client = client is None
    client = client or CDragonClient()
    try:
        if version is None:
            versions = await client.get_json(DDRAGON_VERSIONS)
            version = versions[0]
        log.info("Using Data Dragon version %s", version)

        listing = await client.get_json(ddragon_champion_list(version))
        keys = list(listing.get("data", {}).keys())
        log.info("Found %d champions in DDragon listing", len(keys))

        urls = [ddragon_champion_detail(version, k) for k in keys]
        responses = await asyncio.gather(*(client.get_json(u) for u in urls))

        champions: list[Champion] = []
        for r in responses:
            try:
                detail = next(iter((r.get("data") or {}).values()))
            except StopIteration:
                continue
            try:
                champ = _parse_champion(detail)
            except Exception as e:  # noqa: BLE001
                log.warning("Failed to parse champion %s: %s", detail.get("id"), e)
                continue
            if champ is not None:
                champions.append(champ)
        log.info("Parsed %d champions", len(champions))

        if write:
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            out_path = OUTPUT_DIR / "champions.json"
            out_path.write_text(
                json.dumps(
                    {"version": version, "champions": [c.model_dump(mode="json") for c in champions]},
                    indent=2,
                )
            )
            log.info("Wrote %s", out_path)
        return champions
    finally:
        if owns_client:
            await client.__aexit__(None, None, None)
