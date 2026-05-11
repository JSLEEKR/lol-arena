from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AugmentRarity(str, Enum):
    SILVER = "silver"
    GOLD = "gold"
    PRISMATIC = "prismatic"
    UNKNOWN = "unknown"


class Augment(BaseModel):
    id: int
    name: str
    description: str = ""
    rarity: AugmentRarity = AugmentRarity.UNKNOWN
    # Some augments are champion-specific; key matches Champion.key
    champion_lock: str | None = None
    tags: list[str] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict, exclude=True)
