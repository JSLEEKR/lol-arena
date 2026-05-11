from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ResourceType(str, Enum):
    MANA = "mana"
    ENERGY = "energy"
    FURY = "fury"
    RAGE = "rage"
    FEROCITY = "ferocity"
    HEAT = "heat"
    GNARFURY = "gnarfury"
    NONE = "none"
    HEALTH = "health"
    OTHER = "other"


class ChampionStats(BaseModel):
    """Base + per-level scaling. Computed at level N via .at_level(n)."""

    hp: float
    hp_per_level: float
    hp_regen: float
    hp_regen_per_level: float

    mp: float = 0.0
    mp_per_level: float = 0.0
    mp_regen: float = 0.0
    mp_regen_per_level: float = 0.0

    armor: float
    armor_per_level: float
    mr: float
    mr_per_level: float

    attack_damage: float
    attack_damage_per_level: float
    attack_speed: float
    attack_speed_ratio: float = 0.625
    attack_speed_per_level: float
    attack_range: float
    crit_base: float = 0.0
    crit_per_level: float = 0.0

    movespeed: float

    def at_level(self, level: int) -> dict[str, float]:
        """LoL per-level growth formula: base + growth * (lvl-1) * (0.7025 + 0.0175*(lvl-1))."""
        if not 1 <= level <= 18:
            raise ValueError(f"level must be in [1,18], got {level}")
        n = level - 1
        growth_mult = n * (0.7025 + 0.0175 * n)
        return {
            "hp": self.hp + self.hp_per_level * growth_mult,
            "hp_regen": self.hp_regen + self.hp_regen_per_level * growth_mult,
            "mp": self.mp + self.mp_per_level * growth_mult,
            "mp_regen": self.mp_regen + self.mp_regen_per_level * growth_mult,
            "armor": self.armor + self.armor_per_level * growth_mult,
            "mr": self.mr + self.mr_per_level * growth_mult,
            "attack_damage": self.attack_damage + self.attack_damage_per_level * growth_mult,
            "attack_speed": self.attack_speed * (1 + self.attack_speed_per_level / 100 * growth_mult),
            "movespeed": self.movespeed,
            "attack_range": self.attack_range,
            "crit": self.crit_base + self.crit_per_level * growth_mult,
        }


class AbilitySlot(str, Enum):
    PASSIVE = "P"
    Q = "Q"
    W = "W"
    E = "E"
    R = "R"


class Ability(BaseModel):
    slot: AbilitySlot
    name: str
    description: str = ""
    cooldown: list[float] = Field(default_factory=list)
    cost: list[float] = Field(default_factory=list)
    cost_type: ResourceType = ResourceType.MANA
    range: list[float] = Field(default_factory=list)
    max_rank: int = 5

    # Filled by a later enrichment pass (parsed from description / wiki / bin files)
    raw: dict[str, Any] = Field(default_factory=dict)


class Champion(BaseModel):
    id: int
    key: str  # internal alias e.g. "Garen", "Aatrox"
    name: str
    title: str = ""
    roles: list[str] = Field(default_factory=list)
    resource: ResourceType = ResourceType.MANA
    stats: ChampionStats
    abilities: list[Ability]
    raw: dict[str, Any] = Field(default_factory=dict, exclude=True)
