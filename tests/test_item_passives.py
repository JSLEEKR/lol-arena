"""Test item passive on-hit logic."""

from __future__ import annotations

import pytest

from arena_sim.dps import DUMMIES, auto_dps
from arena_sim.dps.item_passives import compute_on_hit
from arena_sim.models import Champion, ChampionStats, Item, ItemStats, ResourceType
from arena_sim.stats import compose


def _vayne() -> Champion:
    return Champion(
        id=67, key="Vayne", name="Vayne", resource=ResourceType.NONE,
        stats=ChampionStats(
            hp=550, hp_per_level=88, hp_regen=4, hp_regen_per_level=0.5,
            armor=23, armor_per_level=4.2, mr=30, mr_per_level=1.55,
            attack_damage=60, attack_damage_per_level=2.05,
            attack_speed=0.658, attack_speed_per_level=4.0,
            attack_range=590, movespeed=330,
        ),
        abilities=[],
    )


def test_bork_adds_current_hp_magic_damage() -> None:
    bork = Item(id=3153, name="Blade of the Ruined King",
                stats=ItemStats(attack_damage=40, attack_speed_pct=0.25))
    stats = compose(_vayne(), level=11, items=[bork])
    bundle = compute_on_hit(stats, [bork], DUMMIES["squishy"])
    # 12% of 2200 HP = 264 magic damage on-hit (pre-mitigation)
    assert bundle.pre_mitigation_magical == pytest.approx(264)


def test_trinity_force_sheen_proc() -> None:
    trinity = Item(id=3078, name="Trinity Force", stats=ItemStats(attack_damage=36))
    stats = compose(_vayne(), level=11, items=[trinity])
    bundle = compute_on_hit(stats, [trinity], DUMMIES["squishy"])
    assert bundle.sheen_proc_extra_pct_of_base_ad == 2.0


def test_black_cleaver_armor_shred() -> None:
    bc = Item(id=3071, name="Black Cleaver", stats=ItemStats(attack_damage=40, hp=400))
    stats = compose(_vayne(), level=11, items=[bc])
    bundle = compute_on_hit(stats, [bc], DUMMIES["bruiser"])
    assert bundle.armor_shred_pct == pytest.approx(0.24)  # 30% * 80% uptime


def test_auto_dps_includes_on_hit() -> None:
    bork = Item(id=3153, name="Blade of the Ruined King",
                stats=ItemStats(attack_damage=40, attack_speed_pct=0.25, lifesteal=0.1))
    stats = compose(_vayne(), level=11, items=[bork])
    no_items = auto_dps(stats, DUMMIES["squishy"])
    with_items = auto_dps(stats, DUMMIES["squishy"], items=[bork])
    assert with_items.auto_damage > no_items.auto_damage


def test_no_items_no_on_hit() -> None:
    """When items=None, no on-hit is applied (back-compat)."""
    stats = compose(_vayne(), level=1, items=[])
    bundle = compute_on_hit(stats, [], DUMMIES["squishy"])
    assert bundle.pre_mitigation_magical == 0
    assert bundle.sheen_proc_extra_pct_of_base_ad == 0
