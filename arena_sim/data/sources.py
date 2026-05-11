"""Data source endpoint constants.

We use TWO sources:
- Data Dragon (ddragon): Riot's official patch-pinned JSON. Has base stats,
  per-level growth, and spell descriptions. Canonical for champions/items/runes.
- CommunityDragon: community mirror with extras Riot doesn't publish publicly,
  notably the Arena/Cherry augments and raw .bin extracts with spell coefficients.
"""

from __future__ import annotations

# --- Data Dragon (official) ---
DDRAGON_ROOT = "https://ddragon.leagueoflegends.com"
DDRAGON_VERSIONS = f"{DDRAGON_ROOT}/api/versions.json"
DDRAGON_LOCALE = "en_US"  # or "ko_KR"


def ddragon_data(version: str) -> str:
    return f"{DDRAGON_ROOT}/cdn/{version}/data/{DDRAGON_LOCALE}"


def ddragon_champion_list(version: str) -> str:
    return f"{ddragon_data(version)}/champion.json"


def ddragon_champion_detail(version: str, key: str) -> str:
    return f"{ddragon_data(version)}/champion/{key}.json"


def ddragon_items(version: str) -> str:
    return f"{ddragon_data(version)}/item.json"


def ddragon_runes(version: str) -> str:
    return f"{ddragon_data(version)}/runesReforged.json"


# --- CommunityDragon (mirrors + extras) ---
CDRAGON_ROOT = "https://raw.communitydragon.org"
CDRAGON_PATCH = "latest"
CDRAGON_LOCALE = "default"

GAME_DATA = f"{CDRAGON_ROOT}/{CDRAGON_PATCH}/plugins/rcp-be-lol-game-data/global/{CDRAGON_LOCALE}/v1"
CHAMPION_SUMMARY = f"{GAME_DATA}/champion-summary.json"
CHAMPION_DETAIL = f"{GAME_DATA}/champions/{{id}}.json"
PERKS = f"{GAME_DATA}/perks.json"
PERKSTYLES = f"{GAME_DATA}/perkstyles.json"

# Arena / Cherry game mode data
ARENA_BASE = f"{CDRAGON_ROOT}/{CDRAGON_PATCH}/cdragon/arena/en_us.json"

# Raw bin extracts (per-champion, deep coefficient data; large)
CHAMPION_BIN = (
    f"{CDRAGON_ROOT}/{CDRAGON_PATCH}/game/data/characters/{{key_lower}}/{{key_lower}}.bin.json"
)
