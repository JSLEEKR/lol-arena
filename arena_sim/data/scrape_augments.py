"""Arena augment scraper.

Source: https://raw.communitydragon.org/latest/cdragon/arena/en_us.json
Schema varies between patches; we accept either {"augments": [...]} or a top-level list.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from arena_sim.data.client import CDragonClient
from arena_sim.data.sources import ARENA_BASE
from arena_sim.models.augment import Augment, AugmentRarity

log = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"

_RARITY_INT = {
    0: AugmentRarity.SILVER,
    1: AugmentRarity.GOLD,
    2: AugmentRarity.PRISMATIC,
}
_RARITY_STR = {
    "silver": AugmentRarity.SILVER,
    "gold": AugmentRarity.GOLD,
    "prismatic": AugmentRarity.PRISMATIC,
}


def _parse_rarity(raw: Any) -> AugmentRarity:
    if isinstance(raw, int):
        return _RARITY_INT.get(raw, AugmentRarity.UNKNOWN)
    if isinstance(raw, str):
        return _RARITY_STR.get(raw.lower(), AugmentRarity.UNKNOWN)
    return AugmentRarity.UNKNOWN


def _parse_augment(raw: dict[str, Any]) -> Augment | None:
    aid = raw.get("id") or raw.get("contentId")
    name = raw.get("name") or raw.get("displayName")
    if aid is None or not name:
        return None
    # TODO(phase2): detect champion-specific augments from apiName prefix
    champ_lock: str | None = None
    return Augment(
        id=aid if isinstance(aid, int) else hash(str(aid)) & 0x7FFFFFFF,
        name=name,
        description=raw.get("desc") or raw.get("description") or raw.get("tooltip") or "",
        rarity=_parse_rarity(raw.get("rarity")),
        champion_lock=champ_lock,
        tags=[t for t in [raw.get("category")] if t],
        raw=raw,
    )


async def scrape_all(
    client: CDragonClient | None = None,
    *,
    write: bool = True,
) -> list[Augment]:
    owns_client = client is None
    client = client or CDragonClient()
    try:
        payload = await client.get_json(ARENA_BASE)
        if isinstance(payload, dict):
            raw_list = payload.get("augments") or payload.get("data") or []
        elif isinstance(payload, list):
            raw_list = payload
        else:
            raw_list = []

        augments: list[Augment] = []
        for r in raw_list:
            try:
                a = _parse_augment(r)
            except Exception as e:  # noqa: BLE001
                log.warning("Failed to parse augment: %s", e)
                continue
            if a is not None:
                augments.append(a)
        log.info("Parsed %d augments", len(augments))

        if write:
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            out_path = OUTPUT_DIR / "augments.json"
            out_path.write_text(
                json.dumps([a.model_dump(mode="json") for a in augments], indent=2)
            )
            log.info("Wrote %s", out_path)
        return augments
    finally:
        if owns_client:
            await client.__aexit__(None, None, None)
