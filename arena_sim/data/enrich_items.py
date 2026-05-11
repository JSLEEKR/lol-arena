"""Stat enricher: parse stat values from DDragon item description text.

DDragon's `stats` dict only covers ~half of the actual stats on modern items.
Lethality, ability haste, %armor pen, %crit damage, %movespeed, lifesteal,
%omnivamp, magic penetration, tenacity, etc. are only in the description.

We strip HTML and run regex to extract them, then merge into ItemStats.
"""

from __future__ import annotations

import re
from typing import Pattern

from arena_sim.models.item import Item

# Strip every <tag> and </tag>; preserve text.
_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")


def strip_html(s: str) -> str:
    out = _TAG_RE.sub(" ", s)
    return _WHITESPACE_RE.sub(" ", out).strip()


# (pattern, ItemStats field, scale)
# Scale converts the captured number into the value our model expects
# (e.g., "25%" → 0.25 for crit_chance via scale=0.01).
_RULES: list[tuple[Pattern[str], str, float]] = [
    # Ability haste / lethality / pen / vamp — modern shopkeeper phrasing
    (re.compile(r"(\d+(?:\.\d+)?)\s*Ability Haste", re.I), "ability_haste", 1.0),
    (re.compile(r"(\d+(?:\.\d+)?)\s*Lethality", re.I), "lethality", 1.0),
    (re.compile(r"(\d+(?:\.\d+)?)\s*%\s*Armor Pen", re.I), "armor_pen_pct", 0.01),
    (re.compile(r"(\d+(?:\.\d+)?)\s*%\s*Magic Pen", re.I), "magic_pen_pct", 0.01),
    (re.compile(r"(\d+(?:\.\d+)?)\s*Magic Penetration", re.I), "magic_pen_flat", 1.0),
    (re.compile(r"(\d+(?:\.\d+)?)\s*%\s*Critical Strike Damage", re.I), "crit_damage", 0.01),
    (re.compile(r"(\d+(?:\.\d+)?)\s*%\s*Movement Speed", re.I), "movespeed_pct", 0.01),
    (re.compile(r"(\d+(?:\.\d+)?)\s*%\s*Life ?[Ss]teal", re.I), "lifesteal", 0.01),
    (re.compile(r"(\d+(?:\.\d+)?)\s*%\s*Omnivamp", re.I), "omnivamp", 0.01),
    (re.compile(r"(\d+(?:\.\d+)?)\s*%\s*Physical Vamp", re.I), "physical_vamp", 0.01),
    (re.compile(r"(\d+(?:\.\d+)?)\s*%\s*Tenacity", re.I), "tenacity", 0.01),
    (re.compile(r"(\d+(?:\.\d+)?)\s*%\s*Heal[\w\s]*Shield Power", re.I), "heal_shield_power", 0.01),
    (re.compile(r"(\d+(?:\.\d+)?)\s*%\s*Attack Speed", re.I), "attack_speed_pct", 0.01),
    (re.compile(r"(\d+(?:\.\d+)?)\s*Ability Power", re.I), "ability_power", 1.0),
    # These overlap with DDragon's structured stats; skip if already set
    # to avoid double-counting (handled in enrich() below).
    (re.compile(r"(\d+(?:\.\d+)?)\s*Attack Damage", re.I), "attack_damage", 1.0),
    (re.compile(r"(\d+(?:\.\d+)?)\s*Armor(?!\s*Penetration)", re.I), "armor", 1.0),
    (re.compile(r"(\d+(?:\.\d+)?)\s*Magic Resist", re.I), "mr", 1.0),
    (re.compile(r"(\d+(?:\.\d+)?)\s*Health(?!\s*Regen)", re.I), "hp", 1.0),
    (re.compile(r"(\d+(?:\.\d+)?)\s*%\s*Critical Strike Chance", re.I), "crit_chance", 0.01),
]


# DDragon already covers these; the regex would double-count if not gated.
_GATED_FIELDS = {
    "attack_damage", "armor", "mr", "hp", "crit_chance", "ability_power",
    "attack_speed_pct",
}


def enrich_item(item: Item) -> Item:
    """Merge description-extracted stats into the item's structured stats.

    For fields DDragon already provides (AD, armor, MR, HP, crit chance, AP),
    we skip the regex if DDragon's value is non-zero.
    """
    text = strip_html(item.description)
    updates: dict[str, float] = {}
    for pat, field, scale in _RULES:
        m = pat.search(text)
        if not m:
            continue
        val = float(m.group(1)) * scale
        if field in _GATED_FIELDS and getattr(item.stats, field, 0) > 0:
            continue
        # If DDragon's stats had this field but regex picked up a different one,
        # take the larger to avoid wiping a real value.
        existing = getattr(item.stats, field, 0)
        updates[field] = max(existing, val)
    if not updates:
        return item
    merged = item.stats.model_copy(update=updates)
    return item.model_copy(update={"stats": merged})


def enrich_all(items: list[Item]) -> list[Item]:
    return [enrich_item(i) for i in items]
