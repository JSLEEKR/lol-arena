"""Test item description regex enricher."""

from __future__ import annotations

import pytest

from arena_sim.data.enrich_items import enrich_item, strip_html
from arena_sim.models import Item, ItemStats


def test_strip_html() -> None:
    s = "<mainText><attention>50</attention> Attack Damage<br><attention>15</attention> Ability Haste</mainText>"
    assert strip_html(s) == "50 Attack Damage 15 Ability Haste"


def test_enriches_lethality_and_ability_haste() -> None:
    eclipse = Item(
        id=6692, name="Eclipse",
        description="<attention>60</attention> Attack Damage<br><attention>15</attention> Ability Haste",
        stats=ItemStats(attack_damage=60),
    )
    out = enrich_item(eclipse)
    assert out.stats.attack_damage == 60
    assert out.stats.ability_haste == 15


def test_enriches_armor_pen_pct() -> None:
    ldr = Item(
        id=3036, name="Lord Dominik's Regards",
        description="<attention>35</attention> Attack Damage<br><attention>35%</attention> Armor Penetration<br><attention>25%</attention> Critical Strike Chance",
        stats=ItemStats(attack_damage=35, crit_chance=0.25),
    )
    out = enrich_item(ldr)
    assert out.stats.armor_pen_pct == pytest.approx(0.35)


def test_does_not_double_count_gated_fields() -> None:
    bc = Item(
        id=3071, name="Black Cleaver",
        description="<attention>40</attention> Attack Damage<br><attention>400</attention> Health<br><attention>20</attention> Ability Haste",
        stats=ItemStats(attack_damage=40, hp=400),
    )
    out = enrich_item(bc)
    # AD and HP already set; should stay as-is, not double
    assert out.stats.attack_damage == 40
    assert out.stats.hp == 400
    # AH not in DDragon → picked up
    assert out.stats.ability_haste == 20


def test_lifesteal_extracted() -> None:
    bork = Item(
        id=3153, name="Blade of the Ruined King",
        description="<attention>40</attention> Attack Damage<br><attention>25%</attention> Attack Speed<br><attention>10%</attention> Life Steal",
        stats=ItemStats(attack_damage=40),
    )
    out = enrich_item(bork)
    assert out.stats.lifesteal == pytest.approx(0.10)


def test_movespeed_pct() -> None:
    boots = Item(
        id=3009, name="Boots of Swiftness",
        description="<attention>60</attention> Move Speed<br><attention>10%</attention> Movement Speed",
        stats=ItemStats(movespeed_flat=60),
    )
    out = enrich_item(boots)
    assert out.stats.movespeed_pct == pytest.approx(0.10)
