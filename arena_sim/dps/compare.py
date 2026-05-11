"""Build comparison: A vs B, side-by-side diffs."""

from __future__ import annotations

from dataclasses import dataclass

from arena_sim.dps.ability import full_rotation
from arena_sim.dps.auto import auto_dps
from arena_sim.dps.dummies import DUMMIES, Dummy
from arena_sim.models.coefficients import ChampionAbilities
from arena_sim.stats.computed import ComputedStats


@dataclass
class BuildSide:
    label: str
    stats: ComputedStats
    abilities: ChampionAbilities | None = None


@dataclass
class DpsRow:
    target: str
    a_dps: float
    b_dps: float

    @property
    def delta(self) -> float:
        return self.b_dps - self.a_dps

    @property
    def delta_pct(self) -> float:
        return (self.b_dps / self.a_dps - 1) if self.a_dps > 0 else 0.0


def compare_dps(
    a: BuildSide,
    b: BuildSide,
    targets: list[Dummy] | None = None,
    *,
    target_missing_hp_pct: float = 0.0,
) -> list[DpsRow]:
    targets = targets or list(DUMMIES.values())
    rows: list[DpsRow] = []
    for d in targets:
        a_dps = _dps_for(a, d, target_missing_hp_pct)
        b_dps = _dps_for(b, d, target_missing_hp_pct)
        rows.append(DpsRow(target=d.name, a_dps=a_dps, b_dps=b_dps))
    return rows


def _dps_for(side: BuildSide, target: Dummy, missing_hp_pct: float) -> float:
    if side.abilities is not None:
        r = full_rotation(side.abilities, side.stats, target,
                          target_missing_hp_pct=missing_hp_pct)
        return r.sustained_dps
    return auto_dps(side.stats, target).dps


def stat_diff(a: ComputedStats, b: ComputedStats) -> dict[str, tuple[float, float, float]]:
    """Return a dict of stat_name → (a, b, b-a) for human-comparable fields."""
    fields = {
        "HP": (a.hp, b.hp),
        "AD": (a.attack_damage, b.attack_damage),
        "AP": (a.ability_power, b.ability_power),
        "Armor": (a.armor, b.armor),
        "MR": (a.mr, b.mr),
        "AS": (a.attack_speed, b.attack_speed),
        "Crit": (a.crit_chance, b.crit_chance),
        "AbilityHaste": (a.ability_haste, b.ability_haste),
        "Lethality": (a.lethality, b.lethality),
        "ArmorPen%": (a.armor_pen_pct, b.armor_pen_pct),
        "MagicPen": (a.magic_pen_flat, b.magic_pen_flat),
        "Lifesteal": (a.lifesteal, b.lifesteal),
        "Omnivamp": (a.omnivamp, b.omnivamp),
        "Movespeed": (a.effective_movespeed, b.effective_movespeed),
    }
    return {k: (av, bv, bv - av) for k, (av, bv) in fields.items()}
