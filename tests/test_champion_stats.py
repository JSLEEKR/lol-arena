"""Test the Riot per-level growth formula on canonical champions."""

from __future__ import annotations

import pytest

from arena_sim.models import ChampionStats


def garen_stats() -> ChampionStats:
    """Garen base stats from patch 16.9.1."""
    return ChampionStats(
        hp=690,
        hp_per_level=98,
        hp_regen=8,
        hp_regen_per_level=0.5,
        armor=38,
        armor_per_level=4.2,
        mr=32,
        mr_per_level=1.55,
        attack_damage=69,
        attack_damage_per_level=0,
        attack_speed=0.625,
        attack_speed_per_level=3.65,
        attack_range=175,
        movespeed=340,
    )


def test_level_1_returns_base() -> None:
    s = garen_stats()
    out = s.at_level(1)
    assert out["hp"] == pytest.approx(690)
    assert out["armor"] == pytest.approx(38)
    assert out["attack_damage"] == pytest.approx(69)
    assert out["movespeed"] == 340


def test_garen_at_level_11_matches_riot_formula() -> None:
    # base + growth * 10 * (0.7025 + 0.0175*10) = base + growth * 10 * 0.8775
    s = garen_stats()
    out = s.at_level(11)
    assert out["hp"] == pytest.approx(690 + 98 * 10 * 0.8775, rel=1e-6)
    assert out["armor"] == pytest.approx(38 + 4.2 * 10 * 0.8775, rel=1e-6)


def test_level_18_terminal() -> None:
    # base + growth * 17 * (0.7025 + 0.0175*17) = base + growth * 17 * 1.0
    s = garen_stats()
    out = s.at_level(18)
    assert out["hp"] == pytest.approx(690 + 98 * 17 * 1.0, rel=1e-6)
    # Should equal the in-game level 18 max value: 690 + 1666 = 2356
    assert out["hp"] == pytest.approx(2356, abs=1.0)


def test_attack_speed_compounds_percent() -> None:
    # attack_speed grows as base * (1 + per_level/100 * growth_mult)
    s = garen_stats()
    out = s.at_level(18)
    expected = 0.625 * (1 + 3.65 / 100 * 17.0)
    assert out["attack_speed"] == pytest.approx(expected, rel=1e-6)


def test_out_of_range_raises() -> None:
    s = garen_stats()
    with pytest.raises(ValueError):
        s.at_level(0)
    with pytest.raises(ValueError):
        s.at_level(19)
