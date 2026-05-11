# lol-arena

A LoL Arena (Cherry / 2v2v2v2) theorycrafting toolkit.

Pulls every champion, item, augment, and rune from Riot Data Dragon +
CommunityDragon, then computes build stats and DPS so you can compare champion
power across builds — without grinding 50 games.

> **Scope**: pre-simulation only — stat aggregation + DPS calculation.
> No combat engine, no fight resolution.

## Quick demo

```bash
$ arena build inspect --champ Garen --lvl 11 --items "Infinity Edge,Stridebreaker"
                 Garen @ lvl 11
┌───────────────┬──────────────────────────────┐
│ HP            │            2000 (1550 + 450) │
│ AD            │             184.0 (69 + 115) │
│ AP            │                            0 │
│ Armor         │                           75 │
│ MR            │                           46 │
│ AS            │                        0.981 │
│ Crit          │                          25% │
│ Ability Haste │                            0 │
│ Lethality     │                            0 │
│ Movespeed     │                          340 │
└───────────────┴──────────────────────────────┘

$ arena dps run --champ Garen --lvl 11 --items "Infinity Edge,Stridebreaker"
 Garen @ lvl 11 — items: Infinity Edge, Stridebreaker
┌─────────┬───────┬───────────────┬──────────┬──────┐
│ target  │ burst │ sustained DPS │ auto/hit │   AS │
├─────────┼───────┼───────────────┼──────────┼──────┤
│ Naked   │  1457 │           221 │      218 │ 0.98 │
│ Squishy │  1023 │           139 │      137 │ 0.98 │
│ Bruiser │   851 │           107 │      104 │ 0.98 │
│ Tank    │   686 │            76 │       73 │ 0.98 │
└─────────┴───────┴───────────────┴──────────┴──────┘
```

## Status

| Component | Status |
|---|---|
| Data scrapers (champions, items, augments, runes) | ✅ |
| Build stat aggregation (champion + level + items + runes → final stats) | ✅ |
| Auto-attack DPS vs 4 target dummies | ✅ |
| Ability damage calculator + sustained DPS | ✅ (5 champions hand-curated) |
| Lethality / armor pen / crit math | ✅ |
| Ability data for all 172 champions | 🚧 (Garen, Darius, Jhin, Yasuo, Vayne done) |
| Augment effects on damage | 🚧 |
| Item passives (Trinity, BORK, Eclipse, etc.) | 🚧 |
| Build comparison (A vs B side-by-side) | 🚧 |
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
```

## CLI reference

```bash
arena scrape all                       # scrape DDragon + CommunityDragon (idempotent, cached)
arena scrape champions | items | augments | runes

arena build inspect --champ <name> --lvl <1-18> --items "<i1>,<i2>,..."

arena dps run --champ <name> --lvl <1-18> [--items "..."] [--target naked|squishy|bruiser|tank|all] [--missing-hp 0.5]
arena dps list-champions               # champs with hand-curated ability data
```

Item names support fuzzy substring matching: `--items "infinity,stride"` resolves
to "Infinity Edge" and "Stridebreaker".

## Target dummies

DPS is computed against four reference targets, calibrated to mid-Arena builds:

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
├── data/          DDragon + CommunityDragon scrapers, async client, ability loader
├── stats/         Build composition: champ + items + runes → ComputedStats
├── dps/           Auto + ability damage, target dummies, damage math
└── cli.py         typer entry point: scrape, build, dps

data/
├── processed/     Scraped champion/item/augment/rune JSON (gitignored)
└── abilities/     Hand-curated ability coefficient JSON, one file per champion
```

### Data sources

- **[Data Dragon](https://developer.riotgames.com/docs/lol)** — Riot canonical patch data. Used for champions, items, runes.
- **[CommunityDragon](https://www.communitydragon.org/)** — Arena augments + raw `.bin` extracts (future).
- **Hand-curated `data/abilities/<Champion>.json`** — ability damage coefficients, since DDragon strips them for modern champions.

### How DPS is computed

1. **Compose stats**: `ComputedStats = champion.at_level(N) + Σ items.stats + Σ runes.stats` with AS/crit caps applied.
2. **Auto-attack DPS**: `expected_auto_damage × attack_speed` where damage handles crit, armor, and penetration.
3. **Ability rotation**: cast each ability once (using a heuristic skill order for ranks), sum hits, then fill the longest cooldown with autos. Sustained DPS = `(burst + autos_in_window) / window_seconds`.
4. **Mitigation**: Riot's standard `100/(100+armor)` formula, with percent pen applied before flat pen / lethality.

## Roadmap

| Phase | Deliverable | Status |
|---|---|---|
| 1 | Data scrapers | ✅ |
| 2 | Stat aggregation | ✅ |
| 3 | Auto + ability DPS | ✅ |
| 4 | Ability coverage to top 50 Arena champions | 🚧 |
| 5 | Item passives (Trinity proc, BORK %max HP, etc.) | 🚧 |
| 6 | Augment effects layer | — |
| 7 | Side-by-side build comparison | — |
| 8 | Web UI / hosted version | — |

## Contributing

```bash
pip install -e ".[dev]"
ruff check arena_sim tests
pytest -q
```

To add a new champion's ability data, drop a JSON file in `data/abilities/`
following the schema of [`Garen.json`](./data/abilities/Garen.json). Loader is
keyed by filename → champion key.

## License

MIT. See [LICENSE](./LICENSE).

This project is not affiliated with or endorsed by Riot Games. League of Legends is a trademark of Riot Games, Inc.
