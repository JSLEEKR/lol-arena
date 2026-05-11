# lol-arena

A LoL Arena (Cherry / 2v2v2v2) theorycrafting toolkit.

Pulls all champions, items, augments, and runes from Riot Data Dragon +
CommunityDragon, then computes build stats and DPS so you can compare champion
power across builds without actually playing 50 games.

> **Scope**: pre-simulation only — stat aggregation and DPS calculation.
> No combat engine, no AI, no tier list (yet).

## Status

- ✅ Data layer: 172 champions, 705 items, 219 augments, 62 runes (patch 16.9.1)
- 🚧 Build stat aggregation
- 🚧 Auto-attack DPS calculator
- 🚧 Spell coefficient extraction
- 🚧 Ability damage / sustained DPS

## Install

Requires Python 3.11+.

```bash
git clone https://github.com/JSLEEKR/lol-arena.git
cd lol-arena
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
```

## Usage

### Scrape data (idempotent — run once per patch)

```bash
arena scrape all
# → data/processed/{champions,items,augments,runes}.json
```

### Inspect a champion's stats at any level *(coming soon)*

```bash
arena build inspect --champ Garen --lvl 11 --items "Eclipse,Stridebreaker"
```

### Compute DPS *(coming soon)*

```bash
arena dps --champ Garen --lvl 11 \
    --items "Eclipse,Stridebreaker" \
    --augments "Apex Inventor"
```

## Architecture

```
arena_sim/
├── models/        Pydantic schemas: Champion, Item, Augment, Rune
├── data/          DDragon + CommunityDragon scrapers, async client
├── stats/         (build composition: champ + items + runes → final stats)
├── dps/           (auto + ability damage calculators)
└── cli.py         typer entry point
```

### Data sources

- **[Data Dragon](https://developer.riotgames.com/docs/lol)** — Riot's canonical patch data. Used for champions, items, runes.
- **[CommunityDragon](https://www.communitydragon.org/)** — Arena augment data + raw `.bin` extracts for spell coefficients.

## Roadmap

| Phase | Deliverable | Status |
|---|---|---|
| 1 | Data scrapers | ✅ |
| 2 | Build stat aggregation | 🚧 |
| 3 | Auto-attack DPS vs dummies | 🚧 |
| 4 | Spell coefficient extractor | 🚧 |
| 5 | Ability damage calc | 🚧 |
| 6 | Build comparison CLI | 🚧 |
| 7 | Web UI / API | — |

## Contributing

Issues and PRs welcome. Run tests with `pytest`.

## License

MIT. See [LICENSE](./LICENSE).

This project is not affiliated with or endorsed by Riot Games. League of Legends is a trademark of Riot Games, Inc.
