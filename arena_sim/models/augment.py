from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from arena_sim.models.item import ItemStats


class AugmentRarity(str, Enum):
    SILVER = "silver"
    GOLD = "gold"
    PRISMATIC = "prismatic"
    UNKNOWN = "unknown"


class Augment(BaseModel):
    id: int
    name: str
    api_name: str = ""           # internal key like "TheBrutalizer"
    description: str = ""
    rarity: AugmentRarity = AugmentRarity.UNKNOWN
    # Some augments are champion-specific; key matches Champion.key
    champion_lock: str | None = None
    tags: list[str] = Field(default_factory=list)
    # Resolved scalar values from Riot's augment dataValues[0].
    data_values: dict[str, float] = Field(default_factory=dict)
    # Parsed stat boosts. Filled by the enricher; merged into Build stats.
    stat_effects: ItemStats = Field(default_factory=ItemStats)
    raw: dict[str, Any] = Field(default_factory=dict, exclude=True)
