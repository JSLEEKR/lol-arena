"""Stat composition tests."""

from __future__ import annotations

import pytest

from arena_sim.models import (
    Champion,
    ChampionStats,
    Item,
    ItemStats,
    ResourceType,
)
from arena_sim.stats import compose


def _garen() -> Champion:
    return Champion(
        id=86,
        key="Garen",
        name="Garen",
        resource=ResourceType.NONE,
        stats=ChampionStats(
            hp=690, hp_per_level=98, hp_regen=8, hp_regen_per_level=0.5,
            armor=38, armor_per_level=4.2, mr=32, mr_per_level=1.55,
            attack_damage=69, attack_damage_per_level=0,
            attack_speed=0.625, attack_speed_per_level=3.65,
            attack_range=175, movespeed=340,
        ),
        abilities=[],
    )


def test_naked_garen_level_1() -> None:
    s = compose(_garen(), level=1, items=[])
    assert s.attack_damage == 69
    assert s.hp == 690
    assert s.armor == 38
    assert s.attack_speed == pytest.approx(0.625)


def test_garen_lvl_18_with_infinity_edge() -> None:
    ie = Item(id=3031, name="Infinity Edge",
              stats=ItemStats(attack_damage=55, crit_chance=0.25))
    s = compose(_garen(), level=18, items=[ie])
    # base AD at 18 is unchanged (Garen has 0 AD/lvl)
    assert s.base_ad == 69
    assert s.bonus_ad == 55
    assert s.attack_damage == 124
    assert s.crit_chance == 0.25


def test_attack_speed_with_bonus() -> None:
    # 50% bonus AS at level 1 → final = base * 1.5
    bow = Item(id=1043, name="Recurve Bow",
               stats=ItemStats(attack_speed_pct=0.25))
    bow2 = Item(id=1043, name="Bow2",
                stats=ItemStats(attack_speed_pct=0.25))
    s = compose(_garen(), level=1, items=[bow, bow2])
    assert s.attack_speed == pytest.approx(0.625 * 1.5)


def test_attack_speed_capped_at_2_5() -> None:
    super_bow = Item(id=999, name="Mythical Bow",
                     stats=ItemStats(attack_speed_pct=10.0))
    s = compose(_garen(), level=18, items=[super_bow])
    assert s.attack_speed == 2.5


def test_crit_capped_at_1() -> None:
    crit_stacks = [Item(id=i, name=f"Crit{i}", stats=ItemStats(crit_chance=0.5))
                   for i in range(5)]
    s = compose(_garen(), level=1, items=crit_stacks)
    assert s.crit_chance == 1.0


def test_ability_haste_cooldown() -> None:
    haste = Item(id=1, name="Haste Item", stats=ItemStats(ability_haste=20))
    s = compose(_garen(), level=1, items=[haste])
    # 100s base CD with 20 AH → 100 / 1.2 ≈ 83.33s
    assert s.cooldown(100) == pytest.approx(100 / 1.2)


def test_resists_stack_additively() -> None:
    plate = Item(id=1, name="Plate", stats=ItemStats(armor=50))
    cloak = Item(id=2, name="Cloak", stats=ItemStats(mr=40))
    s = compose(_garen(), level=1, items=[plate, cloak])
    assert s.armor == 38 + 50
    assert s.mr == 32 + 40
    assert s.bonus_armor == 50
    assert s.bonus_mr == 40
