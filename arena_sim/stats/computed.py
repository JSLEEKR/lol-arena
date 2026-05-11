"""ComputedStats — the final per-build stat block.

We keep BASE and BONUS separate because LoL ability ratios distinguish them
("+50% bonus AD" only scales off items, not champion base).
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Attack speed cap in standard LoL is 2.5; Arena does not change this for champ APIs.
ATTACK_SPEED_CAP = 2.5
# Ability haste → cooldown reduction: cd_after = cd / (1 + AH/100)
# (no cap; though diminishing returns are inherent to the formula)
CRIT_DAMAGE_BASE = 1.75  # default crit damage multiplier (was 2.0 pre-S11)


@dataclass
class ComputedStats:
    """Final stats for a (champion, level, items, runes) tuple."""

    # Vitals
    base_hp: float = 0.0
    bonus_hp: float = 0.0
    base_mp: float = 0.0
    bonus_mp: float = 0.0
    hp_regen: float = 0.0
    mp_regen: float = 0.0

    # Resistances
    base_armor: float = 0.0
    bonus_armor: float = 0.0
    base_mr: float = 0.0
    bonus_mr: float = 0.0

    # Offense
    base_ad: float = 0.0
    bonus_ad: float = 0.0
    ability_power: float = 0.0
    attack_speed: float = 0.625  # final, capped
    crit_chance: float = 0.0     # 0..1
    crit_damage: float = CRIT_DAMAGE_BASE
    ability_haste: float = 0.0

    # Penetration
    lethality: float = 0.0
    armor_pen_pct: float = 0.0   # 0..1
    magic_pen_flat: float = 0.0
    magic_pen_pct: float = 0.0   # 0..1

    # Vamp
    lifesteal: float = 0.0       # 0..1, physical from autos
    omnivamp: float = 0.0        # 0..1, all damage
    physical_vamp: float = 0.0   # 0..1, physical from anything

    # Mobility
    movespeed: float = 325.0
    movespeed_pct: float = 0.0   # additive bonus % from items/runes

    # Misc
    attack_range: float = 125.0
    tenacity: float = 0.0
    heal_shield_power: float = 0.0

    # Provenance (debug / display)
    champion_key: str = ""
    level: int = 1
    sources: list[str] = field(default_factory=list)

    @property
    def hp(self) -> float:
        return self.base_hp + self.bonus_hp

    @property
    def mp(self) -> float:
        return self.base_mp + self.bonus_mp

    @property
    def armor(self) -> float:
        return self.base_armor + self.bonus_armor

    @property
    def mr(self) -> float:
        return self.base_mr + self.bonus_mr

    @property
    def attack_damage(self) -> float:
        return self.base_ad + self.bonus_ad

    @property
    def effective_movespeed(self) -> float:
        return self.movespeed * (1 + self.movespeed_pct)

    def cooldown(self, base_cd: float) -> float:
        """Apply ability haste to a base cooldown."""
        return base_cd / (1 + self.ability_haste / 100.0)
