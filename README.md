# lol-arena

A LoL theorycrafting toolkit covering **Summoner's Rift, Arena (Cherry), and URF** in one model.

Pulls every champion, item, augment, and rune from Riot Data Dragon +
CommunityDragon, then computes build stats and DPS — so you can compare
champions, builds, and modes without grinding 50 games.

[![tests](https://img.shields.io/badge/tests-74_passing-brightgreen)](#)
[![python](https://img.shields.io/badge/python-3.11+-blue)](#)
[![license](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

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

Modes are a single registry entry — adding a fourth (ARAM, Nexus Blitz, Swarm)
is one dataclass.

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
│ Bruiser │   792 │           110 │       92 │ 0.83 │   ← +33% DPS from URF cooldowns
└─────────┴───────┴───────────────┴──────────┴──────┘
```

Side-by-side build comparison with deltas:

```bash
$ arena dps compare \
    --a-champ Vayne --a-lvl 14 --a-items "Infinity Edge,Phantom Dancer" \
    --b-champ Vayne --b-lvl 14 --b-items "Blade of the Ruined King,Trinity Force" \
    --mode arena
 Sustained DPS
┌─────────┬───────────┬───────────┬──────────┬────────┐
│ Tank    │       359 │       654 │ ▲ +294.6 │ ▲ +82% │   ← BORK+Trinity wins vs tanks
└─────────┴───────────┴───────────┴──────────┴────────┘
```

## HTTP API

```bash
pip install -e ".[api]"
uvicorn arena_sim.api.server:app --reload
```

```bash
$ curl -X POST localhost:8000/dps -H 'Content-Type: application/json' \
       -d '{"champion":"Garen","level":11,"items":["Eclipse","Black Cleaver"],"mode":"urf","target":"bruiser"}'
{
  "champion": "Garen", "level": 11, "mode": "urf",
  "rows": [{"target":"Bruiser","dps":110.2,"burst":791.6,"data_quality":"verified"}]
}
```

Endpoints:
- `GET  /modes` — mode table
- `GET  /champions[?verified_only=true]`
- `GET  /items[?search=...]`
- `GET  /augments[?search=...]`
- `POST /build/inspect` — final stats
- `POST /dps` — auto + ability DPS vs target dummies
- `POST /dps/compare` — A vs B side-by-side

## Status (v1.0.0)

| Component | State |
|---|---|
| Data scrapers (champions / items / augments / runes) | ✅ |
| Multi-mode architecture (Rift / Arena / URF) | ✅ |
| Build stat aggregation (level + items + runes + augments) | ✅ |
| Auto-attack DPS vs 4 target dummies | ✅ |
| Ability damage calculator + sustained DPS | ✅ |
| Item passives: 20+ items (BORK, Trinity, Black Cleaver, Wit's End, Nashor's, Statikk, Stormrazor, RFC, Sheen, Sundered Sky, Spear of Shojin, Voltaic, Lord Dominik's, Liandry's, Shadowflame, …) | ✅ |
| Augment stat effects (auto-extracted from `dataValues` + templates) | ✅ |
| Lethality / armor pen / crit math / magic pen | ✅ |
| FastAPI HTTP server | ✅ |
| All 172 champions loadable | ✅ |
| Ability damage formulas: **28 verified, 144 skeleton** | 🚧 |
| Conditional augments (Apex Inventor, on-hit triggers) | 🚧 |
| Web UI (React/Next.js, hosted) | — |
| Bin extractor (auto-fill skeletons from `.bin` data) | — |

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
arena modes       # available modes
```

## CLI reference

```bash
arena --version | -V
arena scrape all                       # idempotent, cached
arena scrape champions | items | augments | runes
arena info                             # patch version, data counts, curated coverage
arena modes                            # game-mode table
arena list champions|items|augments|abilities [--search SUBSTR]

arena build inspect --champ <name> --lvl <1-18> [--items "..."] [--augments "..."] [--mode arena|rift|urf]

arena dps run     --champ <name> --lvl <1-18> [--items "..."] [--augments "..."] [--target naked|squishy|bruiser|tank|all] [--missing-hp 0.5] [--mode ...]
arena dps compare --a-champ X --a-items "..." [--a-augments "..."] --a-lvl 11 \
                  --b-champ Y --b-items "..." [--b-augments "..."] --b-lvl 11 \
                  [--mode arena|rift|urf]
arena dps list-champions [--all]       # verified vs skeleton split
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

## Data quality

DDragon strips Riot's actual spell coefficients for modern champions
(descriptions still have `{{ damage }}` placeholders), so ability damage data
is **hand-curated**. v1.0 ships with:

- **28 verified champions** (popular Arena/Rift picks). DPS numbers reflect
  real game data.
- **144 skeleton champions**. Ability names + cooldowns + cast ranges are
  pulled from DDragon, but damage formulas are empty. Auto-attack DPS is
  accurate; ability DPS is reported as 0 with a clear warning.

Filling in skeletons is mechanical work — copy a similar champion's JSON,
look up the wiki, verify against in-game tooltips. See
[`data/abilities/Garen.json`](./data/abilities/Garen.json) for the schema.

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
├── api/           FastAPI HTTP wrapper
└── cli.py         typer entry point: scrape, info, modes, list, build, dps

data/
├── processed/     Scraped champion/item/augment/rune JSON (gitignored)
└── abilities/     Ability coefficient JSON, one file per champion
   └── urf/        Optional URF-specific overrides (e.g. Yasuo.json)
   └── arena/      Optional Arena-specific overrides
```

### Adding a new mode

```python
# arena_sim/modes/mode.py
ARAM = ModeModifiers(
    key=GameModeKey.ARAM,
    display_name="Howling Abyss",
    hp_multiplier=1.05,
    cooldown_multiplier=0.85,
    description="ARAM-specific stat boosts.",
)
MODE_REGISTRY[GameModeKey.ARAM] = ARAM
```

That's the full integration — compose() and the DPS pipeline pick it up
automatically. Per-mode ability overrides go in `data/abilities/<mode>/`.

### Adding a champion's ability data

```bash
# Edit data/abilities/<Champion>.json (see data/abilities/Garen.json for the schema)
# Flip "verified": false → true when damage formulas are checked
```

### Data sources

- **[Data Dragon](https://developer.riotgames.com/docs/lol)** — Riot canonical patch data: champions, items, runes.
- **[CommunityDragon](https://www.communitydragon.org/)** — Arena augments (with `dataValues` for stat resolution), `.bin` extracts (future).
- **Hand-curated `data/abilities/<Champion>.json`** — ability damage coefficients.

### How DPS is computed

1. **Compose stats**: `ComputedStats = champion.at_level(N) + Σ items.stats + Σ runes.stats + Σ augments.stat_effects`, with mode modifiers on base stats and AS / crit caps applied last.
2. **Auto-attack DPS**: `expected_auto_damage × attack_speed`; on-hit (BORK, Wit's End, Kraken, …) per AA; armor shred (Black Cleaver) reduces effective armor.
3. **Ability rotation**: cast each ability once (heuristic skill order for rank), sum hits, add Sheen procs per cast, then fill the longest mode-adjusted cooldown with autos. Sustained DPS = `(burst + autos_in_window) / window_seconds`.
4. **Mitigation**: Riot's `100 / (100 + armor)` formula; percent pen applied before flat pen / lethality. Negative resists handled (amplification formula).

## Contributing

```bash
pip install -e ".[dev]"
ruff check arena_sim tests
pytest -q

# Add a champion: copy data/abilities/Garen.json, fill in damage formulas,
# verify against in-game tooltips, flip verified: true.
```

## License

MIT. See [LICENSE](./LICENSE).

This project is not affiliated with or endorsed by Riot Games. League of Legends is a trademark of Riot Games, Inc.
