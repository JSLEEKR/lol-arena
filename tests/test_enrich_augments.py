"""Test augment description templating + stat extraction."""

from __future__ import annotations

import pytest

from arena_sim.data.enrich_augments import _resolve_template, enrich_augment
from arena_sim.models import Augment, AugmentRarity


def test_resolve_simple_var() -> None:
    assert _resolve_template("Gain @AD@ Attack Damage", {"AD": 20}) == "Gain 20 Attack Damage"


def test_resolve_with_multiplier() -> None:
    # @ProcChance*100@ for percent → 0.25 * 100 = 25
    assert _resolve_template(
        "Crit chance increased by @ProcChance*100@%",
        {"ProcChance": 0.25},
    ) == "Crit chance increased by 25%"


def test_resolve_keeps_unknown_var() -> None:
    assert "@Unknown@" in _resolve_template("Gain @Unknown@ stat", {})


def test_brutalizer_extracts_ad_haste_lethality() -> None:
    a = Augment(
        id=82,
        name="The Brutalizer",
        api_name="TheBrutalizer",
        rarity=AugmentRarity.SILVER,
        description="Gain <scaleAD>@AD@ Attack Damage</scaleAD>, @AbilityHaste@ Ability Haste, and <scaleLethality>@Lethality@ Lethality</scaleLethality>.",
        data_values={"AD": 20, "AbilityHaste": 10, "Lethality": 10},
    )
    out = enrich_augment(a)
    assert out.stat_effects.attack_damage == 20
    assert out.stat_effects.ability_haste == 10
    assert out.stat_effects.lethality == 10


def test_witchful_thinking_extracts_ap() -> None:
    a = Augment(
        id=1,
        name="Witchful Thinking",
        api_name="WitchfulThinking",
        rarity=AugmentRarity.SILVER,
        description="Gain @AP@ Ability Power.",
        data_values={"AP": 60},
    )
    out = enrich_augment(a)
    assert out.stat_effects.ability_power == 60


def test_non_stat_augment_yields_empty() -> None:
    a = Augment(
        id=1,
        name="Apex Inventor",
        description="Your last item slot gets a free component.",
    )
    out = enrich_augment(a)
    assert out.stat_effects.attack_damage == 0
    assert out.stat_effects.ability_power == 0


def test_resolved_value_passed_to_compose() -> None:
    """Smoke test that an augment with AD actually shows up in ComputedStats."""
    from arena_sim.models import Champion, ChampionStats, ResourceType
    from arena_sim.stats import compose

    champ = Champion(
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
    aug = enrich_augment(Augment(
        id=82, name="The Brutalizer",
        description="Gain @AD@ Attack Damage, @AbilityHaste@ Ability Haste, and @Lethality@ Lethality.",
        data_values={"AD": 20, "AbilityHaste": 10, "Lethality": 10},
    ))
    stats = compose(champ, level=1, items=[], augments=[aug])
    assert stats.attack_damage == pytest.approx(89)  # 69 base + 20 augment
    assert stats.ability_haste == 10
    assert stats.lethality == 10
