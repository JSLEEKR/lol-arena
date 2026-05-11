"""Item passive effects: on-hit damage, sheen procs, armor shred, etc.

DDragon doesn't expose any of this — passives are free-text in descriptions.
We hand-encode the key items used in Arena, keyed by item name (case-insensitive).

Each passive returns an `OnHit` contribution that the auto-attack DPS path
adds on top of the base auto-attack damage. Sheen-class procs are added to the
ability rotation as an "empowered next AA" hit.
"""

from __future__ import annotations

from dataclasses import dataclass

from arena_sim.dps.damage import DamageType, apply_mitigation
from arena_sim.dps.dummies import Dummy
from arena_sim.models import Item
from arena_sim.stats.computed import ComputedStats


@dataclass(frozen=True)
class OnHitBundle:
    """Net on-hit and damage modifiers for a build.

    pre_mitigation_on_hit: raw damage added to each AA, split by type
    sheen_proc_extra:      damage added to the next AA after every ability cast,
                           computed from (base_ad * mult) — set by Sheen/Trinity/Essence
    armor_shred_pct:       average % armor shred sustained vs target (Black Cleaver)
    """

    pre_mitigation_physical: float = 0.0
    pre_mitigation_magical: float = 0.0
    pre_mitigation_true: float = 0.0
    sheen_proc_extra_pct_of_base_ad: float = 0.0
    armor_shred_pct: float = 0.0


def _has(item_names: set[str], *needles: str) -> bool:
    return any(n in item_names for n in needles)


def compute_on_hit(stats: ComputedStats, items: list[Item], target: Dummy) -> OnHitBundle:
    """Sum the on-hit effects for the given build vs the dummy."""
    names = {i.name.lower() for i in items}
    physical = 0.0
    magical = 0.0
    true_dmg = 0.0
    sheen_pct = 0.0
    armor_shred = 0.0

    # BORK / Kraken Slayer: %current HP magic on-hit (BORK 12%, capped 60 vs minions)
    if _has(names, "blade of the ruined king"):
        magical += target.hp * 0.12
    # Kraken Slayer: every 3rd AA bonus true damage; amortize per AA → bonus_per_hit / 3
    if _has(names, "kraken slayer"):
        true_dmg += (60 + stats.bonus_ad * 0.45) / 3
    # Wit's End: flat 15-80 magic on-hit scaling with level
    if _has(names, "wit's end"):
        magical += 15 + (80 - 15) * (stats.level - 1) / 17
    # Nashor's Tooth: 15 + 20%AP magic on-hit
    if _has(names, "nashor's tooth"):
        magical += 15 + stats.ability_power * 0.20

    # Sheen / Trinity / Essence Reaver: empowered AA after ability
    # Sheen procs every 1.5s; for one-rotation calc we add the proc to next AA.
    if _has(names, "sheen"):
        sheen_pct = max(sheen_pct, 1.0)  # 100% base AD
    if _has(names, "trinity force"):
        sheen_pct = max(sheen_pct, 2.0)  # 200% base AD
    if _has(names, "essence reaver"):
        sheen_pct = max(sheen_pct, 1.4)  # 140% base AD
    if _has(names, "iceborn gauntlet"):
        sheen_pct = max(sheen_pct, 1.0)

    # Black Cleaver: 6% armor reduction per stack, max 5 = 30%. Assume 80% uptime
    # in a sustained DPS calc → 0.30 * 0.8 = 0.24 average.
    if _has(names, "black cleaver"):
        armor_shred = max(armor_shred, 0.30 * 0.8)

    return OnHitBundle(
        pre_mitigation_physical=physical,
        pre_mitigation_magical=magical,
        pre_mitigation_true=true_dmg,
        sheen_proc_extra_pct_of_base_ad=sheen_pct,
        armor_shred_pct=armor_shred,
    )


def apply_on_hit_to_auto(
    base_auto_damage: float,
    bundle: OnHitBundle,
    stats: ComputedStats,
    target: Dummy,
) -> float:
    """Take a base (post-mitigation) auto damage and add on-hit contributions
    correctly mitigated per damage type. Armor shred is already factored into
    target.armor by the caller when constructing the dummy view.
    """
    extra = 0.0
    if bundle.pre_mitigation_physical:
        extra += apply_mitigation(
            bundle.pre_mitigation_physical,
            damage_type=DamageType.PHYSICAL,
            target_armor=target.armor * (1 - bundle.armor_shred_pct),
            target_mr=target.magic_resist,
            armor_pen_pct=stats.armor_pen_pct,
            flat_armor_pen=stats.lethality * (0.6 + 0.4 * stats.level / 18),
        )
    if bundle.pre_mitigation_magical:
        extra += apply_mitigation(
            bundle.pre_mitigation_magical,
            damage_type=DamageType.MAGICAL,
            target_armor=0,
            target_mr=target.magic_resist,
            magic_pen_pct=stats.magic_pen_pct,
            flat_magic_pen=stats.magic_pen_flat,
        )
    if bundle.pre_mitigation_true:
        extra += bundle.pre_mitigation_true
    return base_auto_damage + extra
