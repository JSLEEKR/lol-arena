# lol-arena

A LoL theorycrafting toolkit covering **Summoner's Rift, Arena (Cherry), and URF** in one model.

Pulls every champion, item, augment, and rune from Riot Data Dragon +
CommunityDragon, then computes build stats and DPS so you can compare champions,
builds, and modes — without grinding 50 games.

> Scope: pre-simulation only — stat aggregation + DPS calculation.
> No combat engine, no fight resolution.

## Modes

| Mode | Display | What changes | Augments |
|---|---|---|---|
| `rift` | Summoner's Rift | Baseline (DDragon data as-is) | — |
| `arena` *(default)* | Arena / Cherry 2v2v2v2 | +20% base HP, +5% base AD/AP (round bonuses) | ✓ |
| `urf` | Ultra Rapid Fire | 80% reduced cooldowns (1s floor), no mana, AS cap 3.5 | — |

```bash
arena modes   # show the table above
```

## Quick demo

```bash
$ arena dps run --champ Garen --lvl 11 --items "Eclipse,Black Cleaver" --mode arena
 Garen @ lvl 11 [Arena (Cherry)] — items: Eclipse, Black Cleaver
┌─────────┬───────┬───────────────┬──────────┬──────┐
│ target  │ burst │ sustained DPS │ auto/hit │   AS │
├─────────┼───────┼───────────────┼──────────┼──────┤
│ Bruiser │   797 │            84 │       94 │ 0.83 │
└─────────┴───────┴───────────────┴──────────┴──────┘

$ arena dps run --champ Garen --lvl 11 --items "Eclipse,Black Cleaver" --mode urf
 Garen @ lvl 11 [Ultra Rapid Fire] — items: Eclipse, Black Cleaver
┌─────────┬───────┬───────────────┬──────────┬──────┐
│ Bruiser │   792 │           110 │       92 │ 0.83 │   ← +33% DPS from shorter cooldowns
└─────────┴───────┴───────────────┴──────────┴──────┘
```

Compare two builds side-by-side, with deltas:

```bash
$ arena dps compare \
    --a-champ Vayne --a-lvl 14 --a-items "Infinity Edge,Phantom Dancer" \
    --b-champ Vayne --b-lvl 14 --b-items "Blade of the Ruined King,Trinity Force" \
    --mode arena
 Build Stats — Vayne L14 vs Vayne L14
┌──────────────┬───────────┬───────────┬──────────┐
│ HP           │    2154.4 │    2554.0 │ ▲ +399.6 │
│ AD           │     135.0 │     136.0 │   ▲ +1.0 │
│ Crit         │       50% │        0% │   ▼ -50% │
│ AS           │     1.319 │     1.184 │   ▼ -0.1 │
└──────────────┴───────────┴───────────┴──────────┘
 Sustained DPS
┌─────────┬───────────┬───────────┬──────────┬────────┐
│ Tank    │       359 │       654 │ ▲ +294.6 │ ▲ +82% │   ← BORK+Trinity wins vs tanks
└─────────┴───────────┴───────────┴──────────┴────────┘
```

## Status

| Component | Status |
|---|---|
| Data scrapers (champions / items / augments / runes) | ✅ |
| Multi-mode architecture (Rift / Arena / URF) | ✅ |
| Build stat aggregation (level + items + runes + augments) | ✅ |
| Auto-attack DPS vs 4 target dummies | ✅ |
| Ability damage calculator + sustained DPS | ✅ (28 champions hand-curated) |
| Item passives: BORK / Trinity / Black Cleaver / Wit's End / Nashor's etc. | ✅ |
| Augment stat effects (auto-extracted from dataValues + templates) | ✅ |
| Lethality / armor pen / crit math | ✅ |
| Ability data for remaining 144 champions | 🚧 |
| Conditional augments (Apex Inventor, on-hit triggers) | 🚧 |
| Web UI | — |

## Install

Requires Python 3.11+.

```bash
git clone https://github.com/JSLEEKR/lol-arena.git
cd lol-arena
python3 -m venv .venv && source .venv/bin/activate
pip install -e .

# One-time data scrape (~30 seconds, cached after)
arena scrape all
arena info        # patch + counts
arena modes       # available game modes
```

## CLI reference

```bash
arena scrape all                       # DDragon + CommunityDragon, idempotent + cached
arena scrape champions | items | augments | runes
arena info                             # patch version, data counts, curated coverage
arena modes                            # game-mode table
arena list champions|items|augments|abilities [--search SUBSTR]

arena build inspect --champ <name> --lvl <1-18> [--items "..."] [--augments "..."] [--mode arena|rift|urf]

arena dps run     --champ <name> --lvl <1-18> [--items "..."] [--augments "..."] [--target naked|squishy|bruiser|tank|all] [--missing-hp 0.5] [--mode ...]
arena dps compare --a-champ X --a-items "..." [--a-augments "..."] --a-lvl 11 \
                  --b-champ Y --b-items "..." [--b-augments "..."] --b-lvl 11 \
                  [--mode arena|rift|urf]
arena dps list-champions               # champs with hand-curated ability data
```

Item, augment, and champion names support fuzzy substring matching:
`--items "infinity,stride"` resolves to "Infinity Edge" and "Stridebreaker".

## Target dummies

DPS is computed against four reference targets, calibrated to mid-game builds:

| Dummy | HP | Armor | MR | Represents |
|---|---|---|---|---|
| Naked | 1500 | 0 | 0 | Raw damage benchmark |
| Squishy | 2200 | 60 | 50 | ADC / mage + one defensive item |
| Bruiser | 3200 | 110 | 80 | Fighter with 1.5 defensive items |
| Tank | 4500 | 200 | 150 | Full tank build |

## Architecture

```
arena_sim/
├── models/        Pydantic: Champion, Item, Augment, Rune, AbilityCoefficients
├── data/          DDragon + CommunityDragon scrapers, async client,
│                  description enrichers (items, augments), ability loader
├── modes/         GameMode registry: Rift / Arena / URF; new mode = one dataclass
├── stats/         compose(champ, level, items, runes, augments, mode) → ComputedStats
├── dps/           damage math · auto-attack DPS · ability rotation · item passives
│                  · build comparison · target dummies
└── cli.py         typer entry point: scrape, info, modes, list, build, dps

data/
├── processed/     Scraped champion/item/augment/rune JSON (gitignored)
└── abilities/     Hand-curated ability coefficient JSON, one file per champion
```

### Adding a new mode

```python
# arena_sim/modes/mode.py
NEXUS_BLITZ = ModeModifiers(
    key=GameModeKey.NEXUS_BLITZ,
    display_name="Nexus Blitz",
    cooldown_multiplier=0.85,
    ad_multiplier=1.1,
    description="Faster game with stat boosts.",
)
MODE_REGISTRY[GameModeKey.NEXUS_BLITZ] = NEXUS_BLITZ
```

That's the entire addition — `compose()` and the DPS pipeline pick it up.

### Data sources

- **[Data Dragon](https://developer.riotgames.com/docs/lol)** — Riot canonical patch data: champions, items, runes.
- **[CommunityDragon](https://www.communitydragon.org/)** — Arena augments (incl. `dataValues` for stat resolution), `.bin` extracts (future).
- **Hand-curated `data/abilities/<Champion>.json`** — ability damage coefficients, since DDragon strips them for modern champions.

### How DPS is computed

1. **Compose stats**: `ComputedStats = champion.at_level(N) + Σ items.stats + Σ runes.stats + Σ augments.stat_effects`, with mode modifiers applied to base stats and AS/crit caps applied last.
2. **Auto-attack DPS**: `expected_auto_damage × attack_speed`; on-hit (BORK, Wit's End, Kraken) is added per-AA; armor shred (Black Cleaver) reduces effective armor.
3. **Ability rotation**: cast each ability once (heuristic skill order for rank), sum hits, add Sheen procs per cast, then fill the longest mode-adjusted cooldown with autos. Sustained DPS = `(burst + autos_in_window) / window_seconds`.
4. **Mitigation**: Riot's `100/(100+armor)` formula; percent pen applied before flat pen / lethality. Negative resists handled (amplification formula).

## Contributing

```bash
pip install -e ".[dev]"
ruff check arena_sim tests
pytest -q
```

To add a new champion's ability data, drop a JSON file in `data/abilities/`
following the schema of [`Garen.json`](./data/abilities/Garen.json). The loader
keys by `champion_key` inside the JSON, matching `Champion.key` from DDragon
(note: `MonkeyKing` = Wukong, `Khazix` = Kha'Zix, etc.).

## License

MIT. See [LICENSE](./LICENSE).

This project is not affiliated with or endorsed by Riot Games. League of Legends is a trademark of Riot Games, Inc.
