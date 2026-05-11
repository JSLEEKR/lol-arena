"""Auto-attack DPS calculator."""

from __future__ import annotations

from dataclasses import dataclass

from arena_sim.dps.damage import expected_auto_damage
from arena_sim.dps.dummies import Dummy
from arena_sim.dps.item_passives import OnHitBundle, apply_on_hit_to_auto, compute_on_hit
from arena_sim.models import Item
from arena_sim.stats.computed import ComputedStats


@dataclass(frozen=True)
class AutoDpsResult:
    target: str
    auto_damage: float          # expected per-attack, post-mitigation (incl on-hit)
    auto_damage_raw: float      # pre-mitigation (for diagnostics)
    attack_speed: float         # capped
    dps: float                  # = auto_damage * attack_speed
    time_to_kill: float | None  # vs the dummy's HP, None if AS or damage is zero


def auto_dps(
    stats: ComputedStats,
    target: Dummy,
    items: list[Item] | None = None,
) -> AutoDpsResult:
    """Compute DPS via auto-attacks, including item on-hit effects when items provided."""
    ad = stats.attack_damage
    lvl_factor = 0.6 + 0.4 * stats.level / 18
    flat_pen = stats.lethality * lvl_factor

    bundle: OnHitBundle = compute_on_hit(stats, items, target) if items else OnHitBundle()
    # Black Cleaver shred reduces effective armor for the AA itself.
    eff_armor = target.armor * (1 - bundle.armor_shred_pct)

    base_dmg = expected_auto_damage(
        attack_damage=ad,
        crit_chance=stats.crit_chance,
        crit_damage=stats.crit_damage,
        target_armor=eff_armor,
        flat_armor_pen=flat_pen,
        armor_pen_pct=stats.armor_pen_pct,
    )
    dmg = apply_on_hit_to_auto(base_dmg, bundle, stats, target)
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
