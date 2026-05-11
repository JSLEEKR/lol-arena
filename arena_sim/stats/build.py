"""Build composition: champion + level + items + runes → ComputedStats.

This is the LoL stat aggregation pipeline. Order matters:
  1. Champion base + per-level growth.
  2. Item flat stats (bonus AD, bonus armor, etc.).
  3. Attack speed: champ-level growth + bonus AS% from items, both multiplied
     by the champion's AS ratio (which equals base AS for nearly all champions).
  4. Apply caps (AS at 2.5, crit at 1.0).

Augments are *not* applied here yet — they need event/passive handling
(separate pass once we have a richer mechanism layer).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from arena_sim.models import Augment, Champion, Item, Rune
from arena_sim.stats.computed import ATTACK_SPEED_CAP, ComputedStats


@dataclass
class Build:
    """Inputs for stat composition."""

    champion: Champion
    level: int
    items: list[Item] = field(default_factory=list)
    runes: list[Rune] = field(default_factory=list)
    augments: list[Augment] = field(default_factory=list)

    def compute(self) -> ComputedStats:
        return compose(self.champion, self.level, self.items, self.runes, self.augments)


def compose(
    champion: Champion,
    level: int,
    items: list[Item],
    runes: list[Rune] | None = None,
    augments: list[Augment] | None = None,
) -> ComputedStats:
    runes = runes or []
    augments = augments or []
    base = champion.stats.at_level(level)

    cs = ComputedStats(
        champion_key=champion.key,
        level=level,
        base_hp=base["hp"],
        base_mp=base["mp"],
        hp_regen=base["hp_regen"],
        mp_regen=base["mp_regen"],
        base_armor=base["armor"],
        base_mr=base["mr"],
        base_ad=base["attack_damage"],
        crit_chance=base["crit"],
        movespeed=base["movespeed"],
        attack_range=base["attack_range"],
    )

    # Each stat source contributes a (stats_block, label) pair so the same
    # loop handles items, runes, and augments (which expose stat_effects).
    sources: list[tuple[object, str]] = []
    for it in items:
        sources.append((it.stats, it.name))
    for ru in runes:
        sources.append((getattr(ru, "stats", None), ru.name))
    for au in augments:
        sources.append((au.stat_effects, au.name))

    bonus_as_pct = 0.0
    for stats, src_name in sources:
        if stats is None:
            continue
        cs.bonus_hp += getattr(stats, "hp", 0)
        cs.bonus_mp += getattr(stats, "mp", 0)
        cs.bonus_armor += getattr(stats, "armor", 0)
        cs.bonus_mr += getattr(stats, "mr", 0)
        cs.bonus_ad += getattr(stats, "attack_damage", 0)
        cs.ability_power += getattr(stats, "ability_power", 0)
        cs.crit_chance += getattr(stats, "crit_chance", 0)
        cs.crit_damage += getattr(stats, "crit_damage", 0)
        cs.ability_haste += getattr(stats, "ability_haste", 0)
        cs.lethality += getattr(stats, "lethality", 0)
        cs.armor_pen_pct += getattr(stats, "armor_pen_pct", 0)
        cs.magic_pen_flat += getattr(stats, "magic_pen_flat", 0)
        cs.magic_pen_pct += getattr(stats, "magic_pen_pct", 0)
        cs.lifesteal += getattr(stats, "lifesteal", 0)
        cs.omnivamp += getattr(stats, "omnivamp", 0)
        cs.physical_vamp += getattr(stats, "physical_vamp", 0)
        cs.movespeed += getattr(stats, "movespeed_flat", 0)
        cs.movespeed_pct += getattr(stats, "movespeed_pct", 0)
        cs.tenacity += getattr(stats, "tenacity", 0)
        cs.heal_shield_power += getattr(stats, "heal_shield_power", 0)
        bonus_as_pct += getattr(stats, "attack_speed_pct", 0)
        if src_name:
            cs.sources.append(src_name)

    # Attack speed: champ_base * (1 + level_growth% + bonus%)
    n = level - 1
    growth_mult = n * (0.7025 + 0.0175 * n)
    level_as_pct = champion.stats.attack_speed_per_level / 100.0 * growth_mult
    raw_as = champion.stats.attack_speed * (1 + level_as_pct + bonus_as_pct)
    cs.attack_speed = min(raw_as, ATTACK_SPEED_CAP)

    # Crit chance cap.
    cs.crit_chance = min(cs.crit_chance, 1.0)

    return cs
