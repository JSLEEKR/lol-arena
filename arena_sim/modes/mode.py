"""Game mode definitions: Summoner's Rift, Arena, URF, etc.

A GameMode is a bundle of MULTIPLIERS applied on top of baseline (Rift) data.
New modes are added by:
  1. Adding a value to GameModeKey
  2. Registering a ModeModifiers in MODE_REGISTRY at the bottom of this file
That's it — compose() and the DPS pipeline read the modifier and apply it.

Modifier semantics:
  * stat_multipliers / stat_flat_bonus  → applied at compose() time to ComputedStats
  * cooldown_multiplier                 → ability_cooldown × this (URF = 0.20)
  * cooldown_floor_sec                  → final cooldown floor (URF = 1.0)
  * attack_speed_cap                    → ComputedStats AS cap override
  * mana_cost_multiplier                → spell mana cost × this (URF = 0)
  * augments_available                  → only Arena may apply augments
  * banned_items / required_item_tag    → mode-specific item filters (future)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class GameModeKey(str, Enum):
    RIFT = "rift"       # Summoner's Rift 5v5 (baseline)
    ARENA = "arena"     # Cherry 2v2v2v2 — augments + round stat boosts
    URF = "urf"         # Ultra Rapid Fire — shorter CDs, no mana, higher AS cap


@dataclass(frozen=True)
class ModeModifiers:
    """Per-mode global modifiers applied during stat composition and DPS calc."""

    key: GameModeKey
    display_name: str

    # Stat scalers — multiplicative on the relevant ComputedStats field.
    hp_multiplier: float = 1.0
    ad_multiplier: float = 1.0
    ap_multiplier: float = 1.0
    armor_multiplier: float = 1.0
    mr_multiplier: float = 1.0

    # Flat additions to base stats per level. Arena uses these for round stat boosts.
    flat_hp_bonus: float = 0.0
    flat_ad_bonus: float = 0.0
    flat_ap_bonus: float = 0.0
    flat_armor_bonus: float = 0.0
    flat_mr_bonus: float = 0.0

    # Ability cooldown adjustments. URF reduces by 80% and floors at 1s.
    # Final CD = max(base_cd * cooldown_multiplier, cooldown_floor_sec).
    cooldown_multiplier: float = 1.0
    cooldown_floor_sec: float = 0.0

    # Resource cost reductions.
    mana_cost_multiplier: float = 1.0

    # Caps.
    attack_speed_cap: float = 2.5

    # Mode-specific features.
    augments_available: bool = False
    description: str = ""

    # Extensibility: any additional per-mode constant. Use cautiously.
    extras: dict[str, float] = field(default_factory=dict)


RIFT = ModeModifiers(
    key=GameModeKey.RIFT,
    display_name="Summoner's Rift",
    description="Standard 5v5 — DDragon data applies unmodified.",
)

ARENA = ModeModifiers(
    key=GameModeKey.ARENA,
    display_name="Arena (Cherry)",
    augments_available=True,
    # Arena gives champions ~+20% effective HP and ~+10% damage from passive
    # round bonuses. These are approximate aggregates of multi-round stat boosts.
    hp_multiplier=1.20,
    ad_multiplier=1.05,
    ap_multiplier=1.05,
    description="2v2v2v2 — augments + per-round stat boosts.",
)

URF = ModeModifiers(
    key=GameModeKey.URF,
    display_name="Ultra Rapid Fire",
    cooldown_multiplier=0.20,    # 80% CDR
    cooldown_floor_sec=1.0,      # 1s floor on every ability
    mana_cost_multiplier=0.0,    # no resource costs
    attack_speed_cap=3.5,        # higher AS cap
    description="80% reduced cooldowns, free abilities, higher AS cap.",
)

MODE_REGISTRY: dict[GameModeKey, ModeModifiers] = {
    GameModeKey.RIFT: RIFT,
    GameModeKey.ARENA: ARENA,
    GameModeKey.URF: URF,
}


def get_mode(key: str | GameModeKey) -> ModeModifiers:
    if isinstance(key, str):
        try:
            key = GameModeKey(key.lower())
        except ValueError as e:
            available = ", ".join(m.value for m in GameModeKey)
            raise KeyError(f"Unknown mode {key!r}. Available: {available}") from e
    return MODE_REGISTRY[key]


def list_modes() -> list[ModeModifiers]:
    return list(MODE_REGISTRY.values())
