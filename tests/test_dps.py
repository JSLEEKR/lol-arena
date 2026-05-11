"""Damage formula and DPS calculator tests."""

from __future__ import annotations

import pytest

from arena_sim.dps import DUMMIES, apply_mitigation, auto_dps, expected_auto_damage
from arena_sim.dps.damage import DamageType
from arena_sim.models import Champion, ChampionStats, Item, ItemStats, ResourceType
from arena_sim.stats import compose


def test_armor_mitigation_known_value() -> None:
    # 100 armor → 50% reduction (multiplier 0.5)
    result = apply_mitigation(
        100, damage_type=DamageType.PHYSICAL,
        target_armor=100, target_mr=0,
    )
    assert result == pytest.approx(50)


def test_true_damage_ignores_armor() -> None:
    assert apply_mitigation(100, damage_type=DamageType.TRUE,
                            target_armor=999, target_mr=999) == 100


def test_negative_armor_amplifies() -> None:
    # -100 armor: multiplier = 2 - 100/200 = 1.5
    result = apply_mitigation(100, damage_type=DamageType.PHYSICAL,
                              target_armor=-100, target_mr=0)
    assert result == pytest.approx(150)


def test_percent_armor_pen_applied_first() -> None:
    # 100 armor, 50% pen → eff_armor = 50; 100 raw → 100 * (100/150) = 66.67
    result = apply_mitigation(100, damage_type=DamageType.PHYSICAL,
                              target_armor=100, target_mr=0,
                              armor_pen_pct=0.5)
    assert result == pytest.approx(100 * 100 / 150)


def test_expected_auto_damage_with_crit() -> None:
    # 100 AD, 50% crit chance, 1.75x crit, vs 0 armor
    # expected = 100 * (1 - 0.5 + 0.5 * 1.75) = 100 * 1.375
    result = expected_auto_damage(
        attack_damage=100, crit_chance=0.5, crit_damage=1.75,
        target_armor=0,
    )
    assert result == pytest.approx(137.5)


def _garen() -> Champion:
    return Champion(
        id=86, key="Garen", name="Garen", resource=ResourceType.NONE,
        stats=ChampionStats(
            hp=690, hp_per_level=98, hp_regen=8, hp_regen_per_level=0.5,
            armor=38, armor_per_level=4.2, mr=32, mr_per_level=1.55,
            attack_damage=69, attack_damage_per_level=0,
            attack_speed=0.625, attack_speed_per_level=3.65,
            attack_range=175, movespeed=340,
        ),
        abilities=[],
    )


def test_naked_garen_dps_naked_dummy() -> None:
    stats = compose(_garen(), level=1, items=[])
    r = auto_dps(stats, DUMMIES["naked"])
    # 69 AD * 0.625 AS = 43.125 DPS, no crit, no armor
    assert r.dps == pytest.approx(69 * 0.625)


def test_garen_with_ie_vs_tank() -> None:
    ie = Item(id=3031, name="Infinity Edge",
              stats=ItemStats(attack_damage=55, crit_chance=0.25))
    stats = compose(_garen(), level=18, items=[ie])
    r = auto_dps(stats, DUMMIES["tank"])
    # Tank has 200 armor → 33.3% damage taken. DPS should still be positive.
    assert r.dps > 0
    assert r.time_to_kill is not None
    assert r.time_to_kill > 0
