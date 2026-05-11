"""Parser unit tests for scrapers — no network."""

from __future__ import annotations

from arena_sim.data.scrape_augments import _parse_augment, _parse_rarity
from arena_sim.data.scrape_champions import _parse_champion
from arena_sim.data.scrape_items import _parse_item
from arena_sim.models import AugmentRarity


def test_parse_champion_minimal() -> None:
    raw = {
        "key": "86",
        "id": "Garen",
        "name": "Garen",
        "title": "The Might of Demacia",
        "tags": ["Fighter", "Tank"],
        "partype": "None",
        "stats": {
            "hp": 690, "hpperlevel": 98, "hpregen": 8, "hpregenperlevel": 0.5,
            "mp": 0, "mpperlevel": 0, "mpregen": 0, "mpregenperlevel": 0,
            "armor": 38, "armorperlevel": 4.2,
            "spellblock": 32, "spellblockperlevel": 1.55,
            "attackdamage": 69, "attackdamageperlevel": 0,
            "attackspeed": 0.625, "attackspeedperlevel": 3.65,
            "attackrange": 175, "movespeed": 340,
            "crit": 0, "critperlevel": 0,
        },
        "passive": {"name": "Perseverance", "description": "Out of combat..."},
        "spells": [
            {"name": "Decisive Strike", "description": "...",
             "cooldown": [8, 8, 8, 8, 8], "cost": [0]*5, "range": [550]*5,
             "maxrank": 5},
            {"name": "Courage", "description": "...",
             "cooldown": [22, 19.5, 17, 14.5, 12], "cost": [0]*5, "range": [0]*5,
             "maxrank": 5},
        ],
    }
    c = _parse_champion(raw)
    assert c is not None
    assert c.id == 86
    assert c.key == "Garen"
    assert c.name == "Garen"
    assert c.stats.hp == 690
    assert c.stats.attack_damage == 69
    assert len(c.abilities) == 3  # passive + Q + W
    assert c.abilities[0].slot.value == "P"
    assert c.abilities[1].slot.value == "Q"


def test_parse_champion_rejects_invalid_key() -> None:
    assert _parse_champion({"key": "not-an-int"}) is None
    assert _parse_champion({"key": "0"}) is None
    assert _parse_champion({}) is None


def test_parse_item_extracts_stats() -> None:
    raw = {
        "name": "Infinity Edge",
        "description": "...",
        "gold": {"total": 2500},
        "stats": {
            "FlatPhysicalDamageMod": 55,
            "FlatCritChanceMod": 0.25,
        },
        "tags": ["Damage", "CriticalStrike"],
    }
    item = _parse_item("3031", raw)
    assert item is not None
    assert item.id == 3031
    assert item.name == "Infinity Edge"
    assert item.cost == 2500
    assert item.stats.attack_damage == 55
    assert item.stats.crit_chance == 0.25


def test_parse_rarity_int() -> None:
    assert _parse_rarity(0) == AugmentRarity.SILVER
    assert _parse_rarity(1) == AugmentRarity.GOLD
    assert _parse_rarity(2) == AugmentRarity.PRISMATIC
    assert _parse_rarity(99) == AugmentRarity.UNKNOWN


def test_parse_rarity_str() -> None:
    assert _parse_rarity("silver") == AugmentRarity.SILVER
    assert _parse_rarity("Prismatic") == AugmentRarity.PRISMATIC
    assert _parse_rarity("???") == AugmentRarity.UNKNOWN


def test_parse_augment_basic() -> None:
    raw = {
        "id": 42,
        "name": "Apex Inventor",
        "desc": "Your last item slot ...",
        "rarity": 2,
    }
    a = _parse_augment(raw)
    assert a is not None
    assert a.id == 42
    assert a.rarity == AugmentRarity.PRISMATIC
