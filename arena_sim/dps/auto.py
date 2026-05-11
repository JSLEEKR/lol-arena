"""Auto-attack DPS calculator."""

from __future__ import annotations

from dataclasses import dataclass

from arena_sim.dps.damage import expected_auto_damage
from arena_sim.dps.dummies import Dummy
from arena_sim.stats.computed import ComputedStats


@dataclass(frozen=True)
class AutoDpsResult:
    target: str
    auto_damage: float          # expected per-attack, post-mitigation
    auto_damage_raw: float      # pre-mitigation (for diagnostics)
    attack_speed: float         # capped
    dps: float                  # = auto_damage * attack_speed
    time_to_kill: float | None  # vs the dummy's HP, None if AS or damage is zero


def auto_dps(stats: ComputedStats, target: Dummy) -> AutoDpsResult:
    """Compute DPS via pure auto-attacks, ignoring on-hit effects."""
    ad = stats.attack_damage
    # Lethality is converted to flat armor pen at level 18 (Arena builds tend to be high-level).
    # Standard formula: flat_pen = lethality * (0.6 + 0.4 * lvl/18); use full at lvl 18.
    lvl_factor = 0.6 + 0.4 * stats.level / 18
    flat_pen = stats.lethality * lvl_factor

    dmg = expected_auto_damage(
        attack_damage=ad,
        crit_chance=stats.crit_chance,
        crit_damage=stats.crit_damage,
        target_armor=target.armor,
        flat_armor_pen=flat_pen,
        armor_pen_pct=stats.armor_pen_pct,
    )
    raw = ad * (1 + stats.crit_chance * (stats.crit_damage - 1))

    dps = dmg * stats.attack_speed
    ttk: float | None = target.hp / dps if dps > 0 else None
    return AutoDpsResult(
        target=target.name,
        auto_damage=dmg,
        auto_damage_raw=raw,
        attack_speed=stats.attack_speed,
        dps=dps,
        time_to_kill=ttk,
    )
