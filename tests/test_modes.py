"""Game mode tests: each mode produces its expected modifiers."""

from __future__ import annotations

import pytest

from arena_sim.data.load_abilities import get as get_abilities
from arena_sim.dps import DUMMIES, full_rotation
from arena_sim.models import Augment, Champion, ChampionStats, Item, ItemStats, ResourceType
from arena_sim.modes import ARENA, RIFT, URF, get_mode
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


def test_get_mode_by_string() -> None:
    assert get_mode("rift") is RIFT
    assert get_mode("arena") is ARENA
    assert get_mode("urf") is URF
    assert get_mode("URF") is URF  # case-insensitive


def test_unknown_mode_raises() -> None:
    with pytest.raises(KeyError):
        get_mode("howling-abyss")


def test_rift_baseline_no_change() -> None:
    rift_stats = compose(_garen(), level=11, items=[], mode=RIFT)
    default_stats = compose(_garen(), level=11, items=[])
    assert rift_stats.hp == default_stats.hp
    assert rift_stats.attack_damage == default_stats.attack_damage


def test_arena_hp_multiplier_applied() -> None:
    rift = compose(_garen(), level=11, items=[], mode=RIFT)
    arena = compose(_garen(), level=11, items=[], mode=ARENA)
    assert arena.hp == pytest.approx(rift.hp * 1.20)
    assert arena.attack_damage == pytest.approx(rift.attack_damage * 1.05)
    assert arena.mode_key == "arena"


def test_urf_higher_as_cap() -> None:
    super_bow = Item(id=99, name="MythBow", stats=ItemStats(attack_speed_pct=10.0))
    rift = compose(_garen(), level=18, items=[super_bow], mode=RIFT)
    urf = compose(_garen(), level=18, items=[super_bow], mode=URF)
    assert rift.attack_speed == 2.5
    assert urf.attack_speed == 3.5


def test_urf_cooldown_reduction() -> None:
    stats = compose(_garen(), level=11, items=[], mode=URF)
    # Garen Q base CD = 8s. URF: 8 * 0.2 = 1.6s (above 1.0 floor)
    assert stats.mode_cooldown(8.0) == pytest.approx(1.6)
    # 4s base CD → 4 * 0.2 = 0.8s → floor 1.0s
    assert stats.mode_cooldown(4.0) == 1.0


def test_rift_cooldown_unchanged() -> None:
    stats = compose(_garen(), level=11, items=[], mode=RIFT)
    assert stats.mode_cooldown(8.0) == 8.0  # no AH, no mode change


def test_augments_dropped_outside_arena() -> None:
    aug = Augment(
        id=1, name="X",
        description="Gain @AD@ Attack Damage",
        data_values={"AD": 20},
    )
    # Manually compute the enriched effect (skip enrich_augment for this test)
    aug.stat_effects = ItemStats(attack_damage=20)
    rift = compose(_garen(), level=1, items=[], augments=[aug], mode=RIFT)
    arena = compose(_garen(), level=1, items=[], augments=[aug], mode=ARENA)
    assert rift.bonus_ad == 0   # Augment ignored in non-arena
    assert arena.bonus_ad == 20  # Applied in arena


def test_urf_rotation_uses_shorter_cd() -> None:
    """In URF, Garen's rotation should have a tighter window than in Rift."""
    abilities = get_abilities("Garen")
    if abilities is None:
        pytest.skip("Garen ability data not loaded")

    stats_rift = compose(_garen(), level=11, items=[], mode=RIFT)
    stats_urf = compose(_garen(), level=11, items=[], mode=URF)
    r_rift = full_rotation(abilities, stats_rift, DUMMIES["bruiser"])
    r_urf = full_rotation(abilities, stats_urf, DUMMIES["bruiser"])
    # Same burst (data unchanged), but URF window is shorter → higher sustained.
    assert r_rift.ability_burst == pytest.approx(r_urf.ability_burst)
    assert r_urf.sustained_dps > r_rift.sustained_dps
