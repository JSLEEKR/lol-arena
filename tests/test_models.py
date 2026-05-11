"""Round-trip serialization for all model types."""

from __future__ import annotations

from arena_sim.models import (
    Ability,
    AbilitySlot,
    Augment,
    AugmentRarity,
    Champion,
    ChampionStats,
    Item,
    ItemStats,
    ResourceType,
    Rune,
)


def _garen() -> Champion:
    return Champion(
        id=86,
        key="Garen",
        name="Garen",
        title="The Might of Demacia",
        roles=["Fighter", "Tank"],
        resource=ResourceType.NONE,
        stats=ChampionStats(
            hp=690, hp_per_level=98, hp_regen=8, hp_regen_per_level=0.5,
            armor=38, armor_per_level=4.2, mr=32, mr_per_level=1.55,
            attack_damage=69, attack_damage_per_level=0,
            attack_speed=0.625, attack_speed_per_level=3.65,
            attack_range=175, movespeed=340,
        ),
        abilities=[
            Ability(slot=AbilitySlot.PASSIVE, name="Perseverance", max_rank=1),
            Ability(slot=AbilitySlot.Q, name="Decisive Strike", cooldown=[8]*5, cost=[0]*5),
        ],
    )


def test_champion_roundtrip() -> None:
    c = _garen()
    d = c.model_dump(mode="json")
    c2 = Champion.model_validate(d)
    assert c2 == c


def test_champion_excludes_raw_in_json() -> None:
    c = _garen()
    c.raw = {"big": "blob"}
    d = c.model_dump(mode="json")
    assert "raw" not in d


def test_item_roundtrip() -> None:
    item = Item(id=3031, name="Infinity Edge", cost=2500,
                stats=ItemStats(attack_damage=55, crit_chance=0.25))
    assert Item.model_validate(item.model_dump(mode="json")) == item


def test_augment_roundtrip() -> None:
    a = Augment(id=1, name="Apex Inventor", rarity=AugmentRarity.PRISMATIC,
                description="...")
    assert Augment.model_validate(a.model_dump(mode="json")) == a


def test_rune_roundtrip() -> None:
    r = Rune(id=8005, name="Press the Attack", tree="Precision", slot=0)
    assert Rune.model_validate(r.model_dump(mode="json")) == r
