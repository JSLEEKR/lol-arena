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
    """Sum the on-hit effects for the given build vs the dummy.

    Each branch is a `if _has(...)` check by canonical lower-case item name.
    Where Riot's tooltip uses time-based or proc-conditional damage, we
    amortize per-AA so the DPS calc stays static. Estimates documented inline.
    """
    names = {i.name.lower() for i in items}
    physical = 0.0
    magical = 0.0
    true_dmg = 0.0
    sheen_pct = 0.0
    armor_shred = 0.0
    bonus_vs_hp_pct = 0.0  # Giant Slayer-style damage amp vs high-HP targets

    # ---- pure on-hit damage ----
    # BORK: 12% current HP magic (estimate ~ 12% of current HP per AA, capped vs minions)
    if _has(names, "blade of the ruined king"):
        magical += target.hp * 0.12
    # Kraken Slayer: every 3rd AA bonus true damage; amortize / 3
    if _has(names, "kraken slayer"):
        true_dmg += (60 + stats.bonus_ad * 0.45) / 3
    # Wit's End: flat 15-80 magic on-hit scaling with level
    if _has(names, "wit's end"):
        magical += 15 + (80 - 15) * (stats.level - 1) / 17
    # Nashor's Tooth: 15 + 20%AP magic on-hit
    if _has(names, "nashor's tooth"):
        magical += 15 + stats.ability_power * 0.20
    # Rageblade (Guinsoo's): on-hit doubled-up; approximated as +AA proc of 30 magic
    if _has(names, "guinsoo's rageblade"):
        magical += 30
    # Terminus: alternating modes; avg ~30 magic + 30 physical on-hit
    if _has(names, "terminus"):
        magical += 30
        physical += 30

    # ---- energized items (every ~6 AA-equivalent, amortize per-AA) ----
    # Stormrazor: ~90 + 10%bonus_ad physical every 6 AAs (after move) → /6
    if _has(names, "stormrazor"):
        physical += (90 + stats.bonus_ad * 0.10) / 6
    # Rapid Firecannon: ~80 magic + 30% bonus AD every 6 AAs → /6
    if _has(names, "rapid firecannon"):
        magical += (80 + stats.bonus_ad * 0.30) / 6
    # Statikk Shiv: ~70 magic + 50% AD every 6 AAs (AoE; approximated single-target) → /6
    if _has(names, "statikk shiv"):
        magical += (70 + stats.attack_damage * 0.50) / 6

    # ---- empowered-attack procs (Sheen family) ----
    if _has(names, "sheen"):
        sheen_pct = max(sheen_pct, 1.0)
    if _has(names, "trinity force"):
        sheen_pct = max(sheen_pct, 2.0)
    if _has(names, "essence reaver"):
        sheen_pct = max(sheen_pct, 1.4)
    if _has(names, "iceborn gauntlet"):
        sheen_pct = max(sheen_pct, 1.0)
    # Sundered Sky: Lightshield procs ~every 8s, empowered AA crits → ~+50% base AD
    # per ability cast; approximated as 0.5x sheen.
    if _has(names, "sundered sky"):
        sheen_pct = max(sheen_pct, 0.6)
    # Spear of Shojin: bonus damage on abilities. Modeled as a half-strength sheen.
    if _has(names, "spear of shojin"):
        sheen_pct = max(sheen_pct, 0.5)
    # Voltaic Cyclosword: after dash/blink, next AA deals ~125 + 60% bonus_ad
    # physical. In Arena, dashes happen ~every 8s → approximate as
    # 0.3x sheen-proc-equivalent if user runs a mobility champ.
    if _has(names, "voltaic cyclosword"):
        physical += 12 + stats.bonus_ad * 0.06  # amortized per-AA value

    # ---- armor shred / magic pen / multipliers ----
    # Black Cleaver: 6% armor reduction per stack, max 5 = 30%. ~80% uptime → 24% avg.
    if _has(names, "black cleaver"):
        armor_shred = max(armor_shred, 0.30 * 0.8)

    # Lord Dominik's Regards: Giant Slayer — up to +15% damage vs targets with
    # more bonus HP. Approximate vs tank dummy ≈ +15%; vs squishy ≈ +3%.
    if _has(names, "lord dominik's regards"):
        # crude HP-based scaler: tank=15%, bruiser=8%, squishy=3%, naked=0%
        diff = max(target.hp - 1800, 0) / (4500 - 1800)
        bonus_vs_hp_pct = max(bonus_vs_hp_pct, 0.15 * min(diff, 1.0))

    # Liandry's Torment: 2% max HP magic damage per second (burn). Per-AA at
    # 1 AA/s → 2% max HP magic per AA, capped at 50% over duration in lore.
    if _has(names, "liandry's torment") or _has(names, "liandry's anguish"):
        magical += target.hp * 0.02

    # Shadowflame: bonus magic damage on low-HP targets, +20% crit on magic damage.
    # Approximated as flat +10% magic effective.
    if _has(names, "shadowflame"):
        magical *= 1.10

    # ---- multiplicative against target HP bracket ----
    if bonus_vs_hp_pct > 0:
        physical *= 1 + bonus_vs_hp_pct
        magical *= 1 + bonus_vs_hp_pct
        true_dmg *= 1 + bonus_vs_hp_pct

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
