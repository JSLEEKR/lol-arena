"""Ability damage calculator.

Burst = sum of all ability hits in a single rotation, post-mitigation.
Sustained DPS = (burst + auto contribution over rotation_time) / rotation_time.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from arena_sim.dps.auto import auto_dps
from arena_sim.dps.damage import DamageType, apply_mitigation
from arena_sim.dps.dummies import Dummy
from arena_sim.dps.item_passives import compute_on_hit
from arena_sim.models import Item
from arena_sim.models.coefficients import AbilityCoefficients, ChampionAbilities, DamageKind, Hit
from arena_sim.stats.computed import ComputedStats

_DAMAGE_KIND_TO_TYPE = {
    DamageKind.PHYSICAL: DamageType.PHYSICAL,
    DamageKind.MAGICAL: DamageType.MAGICAL,
    DamageKind.TRUE: DamageType.TRUE,
}


def _ratio_value(key: str, stats: ComputedStats, target: Dummy) -> float:
    """Resolve a RatioKey to its actual scaling value."""
    if key == "total_ad":
        return stats.attack_damage
    if key == "bonus_ad":
        return stats.bonus_ad
    if key == "ap":
        return stats.ability_power
    if key == "max_hp":
        return target.hp
    if key == "missing_hp":
        # Conservative: treat target as full HP for "missing HP" portions —
        # this UNDER-counts execute spells. Users running execute math should
        # call expected_damage with target_hp_pct.
        return 0.0
    if key == "current_hp":
        return target.hp
    if key == "caster_max_hp":
        return stats.hp
    if key == "caster_bonus_hp":
        return stats.bonus_hp
    if key == "level":
        return float(stats.level)
    return 0.0


def hit_damage(
    hit: Hit,
    rank: int,
    stats: ComputedStats,
    target: Dummy,
    *,
    target_missing_hp_pct: float = 0.0,
) -> float:
    """Compute post-mitigation damage of one Hit at a given rank.

    rank is 1-indexed (matches in-game R1/R2/R3 etc.).
    target_missing_hp_pct lets you model execute spells: e.g. 0.7 means target
    is at 30% HP; missing_hp ratio uses (target.hp * 0.7).
    """
    base = hit.base[rank - 1] if hit.base and 1 <= rank <= len(hit.base) else 0.0
    raw = base
    for ratio_key, mult in hit.ratios.items():
        if ratio_key == "missing_hp":
            raw += target.hp * target_missing_hp_pct * mult
        elif ratio_key == "current_hp":
            raw += target.hp * (1 - target_missing_hp_pct) * mult
        else:
            raw += _ratio_value(ratio_key, stats, target) * mult

    # Crit on auto-empowering abilities (Yasuo Q, Vayne Q empowered AA, etc.)
    if hit.can_crit and stats.crit_chance > 0:
        crit_mult = 1 - stats.crit_chance + stats.crit_chance * stats.crit_damage
        raw *= crit_mult

    # Lethality → flat armor pen at this level.
    lvl_factor = 0.6 + 0.4 * stats.level / 18
    flat_armor_pen = stats.lethality * lvl_factor

    return apply_mitigation(
        raw,
        damage_type=_DAMAGE_KIND_TO_TYPE[hit.damage_type],
        target_armor=target.armor,
        target_mr=target.magic_resist,
        flat_armor_pen=flat_armor_pen,
        armor_pen_pct=stats.armor_pen_pct,
        flat_magic_pen=stats.magic_pen_flat,
        magic_pen_pct=stats.magic_pen_pct,
    )


def ability_damage(
    ability: AbilityCoefficients,
    rank: int,
    stats: ComputedStats,
    target: Dummy,
    *,
    target_missing_hp_pct: float = 0.0,
) -> float:
    """Sum all hits across an ability's repeats."""
    return ability.repeat * sum(
        hit_damage(h, rank, stats, target, target_missing_hp_pct=target_missing_hp_pct)
        for h in ability.hits
    )


@dataclass
class RotationReport:
    champion_key: str
    target: str
    abilities_used: list[str]
    ability_burst: float  # total ability damage in one rotation
    rotation_time: float  # seconds (sum of cast_times)
    autos_in_window: float  # number of autos that fit in cooldown of longest ability
    auto_damage_per_attack: float
    sustained_dps: float
    breakdown: dict[str, float] = field(default_factory=dict)


def _rank_for_slot(slot: str, level: int) -> int:
    """Approximation of typical skill order: max Q > E > W, level R at 6/11/16."""
    if slot == "R":
        return 1 if level < 11 else 2 if level < 16 else 3
    # For Q/W/E: assume skilled like a normal champion (max one ability)
    # We default to capping at level 5 by level 9, level 3 by level 5.
    return min(5, max(1, (level + 1) // 2))


def full_rotation(
    abilities: ChampionAbilities,
    stats: ComputedStats,
    target: Dummy,
    *,
    target_missing_hp_pct: float = 0.0,
    items: list[Item] | None = None,
) -> RotationReport:
    """One combo: use every ability once, then auto-attack in the gap until longest CD ends.

    If `items` are provided, on-hit effects (BORK, Wit's End, etc.) are added to
    autos, and Sheen-class procs are added to the first AA after each ability.
    """
    used: list[str] = []
    burst = 0.0
    breakdown: dict[str, float] = {}
    rotation_time = 0.0
    longest_cd = 0.0
    abilities_cast = 0

    for slot in ("Q", "W", "E", "R"):
        ab = abilities.abilities.get(slot)
        if ab is None or not ab.hits:
            continue
        rank = _rank_for_slot(slot, stats.level)
        rank = min(rank, max((len(h.base) for h in ab.hits if h.base), default=1))
        dmg = ability_damage(ab, rank, stats, target,
                             target_missing_hp_pct=target_missing_hp_pct)
        used.append(slot)
        burst += dmg
        breakdown[f"{slot} ({ab.name})"] = dmg
        rotation_time += ab.cast_time
        abilities_cast += 1
        cd_arr = ab.cooldown or []
        cd = cd_arr[min(rank, len(cd_arr)) - 1] if cd_arr else 0.0
        cd = stats.cooldown(cd)
        longest_cd = max(longest_cd, cd)

    auto = auto_dps(stats, target, items=items)
    breakdown[f"Auto ({stats.attack_speed:.2f} AS)"] = auto.auto_damage

    # Sheen proc: one empowered AA per ability cast (in a single rotation).
    sheen_burst = 0.0
    if items:
        bundle = compute_on_hit(stats, items, target)
        if bundle.sheen_proc_extra_pct_of_base_ad > 0 and abilities_cast > 0:
            from arena_sim.dps.damage import apply_mitigation
            lvl_factor = 0.6 + 0.4 * stats.level / 18
            flat_pen = stats.lethality * lvl_factor
            raw = stats.base_ad * bundle.sheen_proc_extra_pct_of_base_ad
            per_proc = apply_mitigation(
                raw, damage_type=DamageType.PHYSICAL,
                target_armor=target.armor * (1 - bundle.armor_shred_pct),
                target_mr=target.magic_resist,
                flat_armor_pen=flat_pen,
                armor_pen_pct=stats.armor_pen_pct,
            )
            sheen_burst = per_proc * abilities_cast
            breakdown["Sheen procs"] = sheen_burst
            burst += sheen_burst

    window = max(rotation_time, longest_cd)
    autos_in_window = max(window - rotation_time, 0.0) * stats.attack_speed
    auto_burst_in_window = autos_in_window * auto.auto_damage
    sustained = (burst + auto_burst_in_window) / window if window > 0 else 0.0

    return RotationReport(
        champion_key=abilities.champion_key,
        target=target.name,
        abilities_used=used,
        ability_burst=burst,
        rotation_time=window,
        autos_in_window=autos_in_window,
        auto_damage_per_attack=auto.auto_damage,
        sustained_dps=sustained,
        breakdown=breakdown,
    )
