"""Structured ability damage coefficients.

DDragon doesn't expose the actual numerical values for modern champion spells
(they live in Riot's .bin files). We capture the canonical data in JSON files
under data/abilities/<champion_key>.json that this module loads.

Scope of a 'Hit':
  - one discrete damage instance from an ability
  - e.g., Garen E's per-spin damage is one Hit; final cleave is another Hit
  - cleanly composes — burst = sum of hits, sustained DPS = burst / rotation_time
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class DamageKind(str, Enum):
    PHYSICAL = "physical"
    MAGICAL = "magical"
    TRUE = "true"


# Names of supported ratio fields. Each maps to a ComputedStats accessor when
# computing damage. New scaling types should be added here AND in arena_sim/dps/ability.py.
RatioKey = Literal[
    "total_ad",      # full AD (base + bonus)
    "bonus_ad",      # bonus AD only (items)
    "ap",            # ability power
    "max_hp",        # target's max HP %
    "missing_hp",    # target's missing HP %
    "current_hp",    # target's current HP %
    "caster_max_hp",  # caster's max HP %
    "caster_bonus_hp",  # caster's bonus HP
    "level",         # caster's level (rare; some on-hit effects)
]


class Hit(BaseModel):
    """A single damage instance within an ability."""

    name: str = ""
    damage_type: DamageKind
    base: list[float] = Field(default_factory=list)  # per-rank base damage
    ratios: dict[RatioKey, float] = Field(default_factory=dict)
    can_crit: bool = False
    aoe: bool = False


class AbilityCoefficients(BaseModel):
    """All damage hits for one ability, plus timing."""

    slot: Literal["P", "Q", "W", "E", "R"]
    name: str
    cooldown: list[float] = Field(default_factory=list)
    cast_time: float = 0.25  # seconds, for sustained DPS calc
    hits: list[Hit] = Field(default_factory=list)
    repeat: int = 1  # number of times the hits trigger per cast (e.g. Garen E spins)


class ChampionAbilities(BaseModel):
    """All abilities for a single champion."""

    champion_key: str
    abilities: dict[str, AbilityCoefficients] = Field(default_factory=dict)
