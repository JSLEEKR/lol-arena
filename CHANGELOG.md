# Changelog

## 1.0.0 — 2026-05-11

First stable release. Core engine, three game modes, every champion loadable,
HTTP API.

### Added

- **All 172 champions loadable.** 28 with hand-verified ability damage data;
  144 with auto-generated skeletons (cooldowns and ability names correct,
  damage formulas pending — these run auto-attack-only DPS with a warning).
- **`verified` flag** on `ChampionAbilities`. `arena dps run` warns when
  computing DPS from unverified data. `arena dps list-champions [--all]`
  separates verified from skeleton.
- **20+ item passive effects** including BORK, Kraken Slayer, Wit's End,
  Nashor's Tooth, Rageblade, Terminus, Stormrazor, Rapid Firecannon,
  Statikk Shiv, Sheen / Trinity / Essence Reaver / Iceborn Gauntlet,
  Sundered Sky, Spear of Shojin, Voltaic Cyclosword, Black Cleaver,
  Lord Dominik's, Liandry's, Shadowflame.
- **FastAPI HTTP server** (`pip install -e ".[api]"`) exposing the same
  engine the CLI uses: `/modes`, `/champions`, `/items`, `/augments`,
  `/build/inspect`, `/dps`, `/dps/compare`.

### Changed

- Bumped `arena-sim` to `1.0.0` and reframed README around the three modes
  (Rift / Arena / URF) instead of Arena-only.

### Known limitations

- 144 of 172 champions have only auto-attack-accurate DPS. Filling in damage
  formulas is incremental, manual work tracked in `data/abilities/`.
- Some augment effects (conditional triggers like Apex Inventor, on-hit
  enchants) are not yet modelled — only stat-modifier augments work.
- Item passives use static approximations for time-based / proc-based
  effects (energized items, sheen procs). Documented inline in
  `arena_sim/dps/item_passives.py`.

## 0.2.0 — 2026-05-11

- Multi-mode support: Summoner's Rift / Arena / URF, extensible mode registry,
  per-mode ability override directories.
- Augment stat enricher (resolves `@AD@` templates against Riot's `dataValues`).
- Item description enricher (lethality, AH, %pen, %ms, etc. that DDragon's
  structured stats dict omits).
- Build comparison: `arena dps compare`.
- Item passives: BORK on-hit, Trinity sheen procs, Black Cleaver armor shred,
  etc.
- 28 hand-curated champions.
- CLI polish: `--version`, `arena info`, `arena modes`, `arena list`.

## 0.1.0 — 2026-05-11

- Initial release: data scrapers (DDragon + CommunityDragon), Pydantic models,
  level-aware base stat calculation, auto-attack DPS, ability rotation engine,
  5 hand-curated champions.
