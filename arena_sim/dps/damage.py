"""Core LoL damage math: armor / MR mitigation, penetration, crit expectation."""

from __future__ import annotations

from enum import Enum


class DamageType(str, Enum):
    PHYSICAL = "physical"
    MAGICAL = "magical"
    TRUE = "true"


def apply_mitigation(
    raw_damage: float,
    *,
    damage_type: DamageType,
    target_armor: float,
    target_mr: float,
    flat_armor_pen: float = 0.0,
    armor_pen_pct: float = 0.0,
    flat_magic_pen: float = 0.0,
    magic_pen_pct: float = 0.0,
) -> float:
    """Apply Riot's standard damage reduction formula.

    Penetration order (the order matters!):
      1. Percent armor reduction (rare; e.g., Black Cleaver)
      2. Percent armor penetration (e.g., Last Whisper)
      3. Flat armor penetration / lethality (last)
    For magic damage: % magic pen first, then flat magic pen.
    Negative resists use the inverted formula.
    """
    if damage_type == DamageType.TRUE:
        return raw_damage

    if damage_type == DamageType.PHYSICAL:
        # Percent armor pen first, then flat (lethality is already passed as flat).
        eff_armor = target_armor * (1 - armor_pen_pct) - flat_armor_pen
    else:
        eff_armor = target_mr * (1 - magic_pen_pct) - flat_magic_pen

    if eff_armor >= 0:
        multiplier = 100 / (100 + eff_armor)
    else:
        # Reduced (sub-zero) resist amplifies damage.
        multiplier = 2 - 100 / (100 - eff_armor)
    return raw_damage * multiplier


def expected_auto_damage(
    *,
    attack_damage: float,
    crit_chance: float,
    crit_damage: float,
    target_armor: float,
    flat_armor_pen: float = 0.0,
    armor_pen_pct: float = 0.0,
) -> float:
    """Expected damage of a single auto-attack vs an armored target.

    Combines crit chance × crit damage with armor mitigation.
    Does not yet include on-hit (Black Cleaver, BORK, etc.) — flagged for phase 2.
    """
    non_crit = attack_damage
    crit = attack_damage * crit_damage
    raw = non_crit * (1 - crit_chance) + crit * crit_chance
    return apply_mitigation(
        raw,
        damage_type=DamageType.PHYSICAL,
        target_armor=target_armor,
        target_mr=0,
        flat_armor_pen=flat_armor_pen,
        armor_pen_pct=armor_pen_pct,
    )
