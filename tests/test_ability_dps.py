"""Ability damage + rotation tests."""

from __future__ import annotations

import pytest

from arena_sim.data.load_abilities import load_all
from arena_sim.dps import DUMMIES, full_rotation, hit_damage
from arena_sim.models import Champion, ChampionStats, Item, ItemStats, ResourceType
from arena_sim.models.coefficients import DamageKind, Hit
from arena_sim.stats import compose


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


def test_hit_damage_simple_physical() -> None:
    hit = Hit(name="t", damage_type=DamageKind.PHYSICAL, base=[100], ratios={"total_ad": 1.0})
    stats = compose(_garen(), level=1, items=[])
    dmg = hit_damage(hit, rank=1, stats=stats, target=DUMMIES["naked"])
    # base 100 + AD 69 = 169 raw, naked target → 169
    assert dmg == pytest.approx(169)


def test_hit_damage_armor_mitigation() -> None:
    hit = Hit(name="t", damage_type=DamageKind.PHYSICAL, base=[100])
    stats = compose(_garen(), level=1, items=[])
    dmg = hit_damage(hit, rank=1, stats=stats, target=DUMMIES["tank"])
    # 100 raw vs 200 armor → 100 * 100/300 ≈ 33.33
    assert dmg == pytest.approx(100 * 100 / 300)


def test_hit_damage_true_ignores_armor() -> None:
    hit = Hit(name="t", damage_type=DamageKind.TRUE, base=[100])
    stats = compose(_garen(), level=1, items=[])
    assert hit_damage(hit, 1, stats, DUMMIES["tank"]) == pytest.approx(100)


def test_hit_damage_missing_hp() -> None:
    hit = Hit(name="exec", damage_type=DamageKind.TRUE, base=[100],
              ratios={"missing_hp": 0.25})
    stats = compose(_garen(), level=1, items=[])
    # naked dummy 1500 HP at 50% → missing 750 → 0.25 * 750 = 187.5 bonus
    dmg = hit_damage(hit, 1, stats, DUMMIES["naked"], target_missing_hp_pct=0.5)
    assert dmg == pytest.approx(100 + 1500 * 0.5 * 0.25)


def test_garen_rotation_loads_real_data() -> None:
    libs = load_all()
    assert "Garen" in libs
    abs_ = libs["Garen"]
    assert "Q" in abs_.abilities
    assert "E" in abs_.abilities
    assert "R" in abs_.abilities

    ie = Item(id=3031, name="IE", stats=ItemStats(attack_damage=55, crit_chance=0.25))
    stats = compose(_garen(), level=11, items=[ie])
    r = full_rotation(abs_, stats, DUMMIES["bruiser"])
    assert r.ability_burst > 0
    assert r.sustained_dps > 0
    assert "Q" in r.abilities_used
    assert "E" in r.abilities_used
