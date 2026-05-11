from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ItemStats(BaseModel):
    """Flat stats granted by an item. Percent fields are 0..1."""

    attack_damage: float = 0.0
    ability_power: float = 0.0
    hp: float = 0.0
    mp: float = 0.0
    armor: float = 0.0
    mr: float = 0.0
    attack_speed_pct: float = 0.0
    ability_haste: float = 0.0
    crit_chance: float = 0.0
    crit_damage: float = 0.0
    movespeed_flat: float = 0.0
    movespeed_pct: float = 0.0
    lethality: float = 0.0
    armor_pen_pct: float = 0.0
    magic_pen_flat: float = 0.0
    magic_pen_pct: float = 0.0
    omnivamp: float = 0.0
    physical_vamp: float = 0.0
    lifesteal: float = 0.0
    tenacity: float = 0.0
    heal_shield_power: float = 0.0


class Item(BaseModel):
    id: int
    name: str
    description: str = ""
    cost: int = 0
    is_arena_prismatic: bool = False
    is_arena_only: bool = False
    tags: list[str] = Field(default_factory=list)
    stats: ItemStats = Field(default_factory=ItemStats)
    raw: dict[str, Any] = Field(default_factory=dict, exclude=True)
