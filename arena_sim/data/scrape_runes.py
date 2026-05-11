"""Rune scraper using Data Dragon's runesReforged.json.

Shape: top-level is a list of trees; each tree has {id, key, name, slots: [{runes: [...]}]}.
Slot index 0 is the keystone row; 1..3 are minor rune rows.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from arena_sim.data.client import CDragonClient
from arena_sim.data.sources import DDRAGON_VERSIONS, ddragon_runes
from arena_sim.models.rune import Rune

log = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"


async def scrape_all(
    client: CDragonClient | None = None,
    *,
    write: bool = True,
    version: str | None = None,
) -> list[Rune]:
    owns_client = client is None
    client = client or CDragonClient()
    try:
        if version is None:
            versions = await client.get_json(DDRAGON_VERSIONS)
            version = versions[0]
        trees = await client.get_json(ddragon_runes(version))

        runes: list[Rune] = []
        for tree in trees:
            tree_name = tree.get("name", "")
            for slot_idx, slot in enumerate(tree.get("slots", [])):
                for r in slot.get("runes", []):
                    try:
                        runes.append(
                            Rune(
                                id=r["id"],
                                name=r.get("name", ""),
                                description=r.get("longDesc") or r.get("shortDesc") or "",
                                tree=tree_name,
                                slot=slot_idx,
                                raw=r,
                            )
                        )
                    except Exception as e:  # noqa: BLE001
                        log.warning("Failed to parse rune id=%s: %s", r.get("id"), e)

        log.info("Parsed %d runes across %d trees", len(runes), len(trees))

        if write:
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            out_path = OUTPUT_DIR / "runes.json"
            out_path.write_text(
                json.dumps(
                    {"version": version, "runes": [r.model_dump(mode="json") for r in runes]},
                    indent=2,
                )
            )
            log.info("Wrote %s", out_path)
        return runes
    finally:
        if owns_client:
            await client.__aexit__(None, None, None)
