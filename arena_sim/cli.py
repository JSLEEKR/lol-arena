"""arena CLI: scrape data, inspect builds, compute DPS."""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

from arena_sim.data import scrape_augments, scrape_champions, scrape_items, scrape_runes
from arena_sim.data.load_abilities import available_keys as ability_keys
from arena_sim.data.load_abilities import get as get_abilities
from arena_sim.dps import DUMMIES, auto_dps, full_rotation
from arena_sim.models import Champion, Item
from arena_sim.stats import compose

console = Console()
app = typer.Typer(no_args_is_help=True, add_completion=False, rich_markup_mode="rich")
scrape_app = typer.Typer(no_args_is_help=True, help="Pull data from CommunityDragon / DDragon.")
build_app = typer.Typer(no_args_is_help=True, help="Inspect builds and stats.")
dps_app = typer.Typer(no_args_is_help=True, help="Compute DPS for champion builds.")
app.add_typer(scrape_app, name="scrape")
app.add_typer(build_app, name="build")
app.add_typer(dps_app, name="dps")


def _configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.WARNING,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, show_path=False, markup=True)],
    )


DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "processed"


def _load_champions() -> dict[str, Champion]:
    path = DATA_DIR / "champions.json"
    if not path.exists():
        console.print(
            f"[red]Champion data not found at {path}.[/red] "
            "Run [bold]arena scrape champions[/bold] first."
        )
        raise typer.Exit(2)
    blob = json.loads(path.read_text())
    return {c["key"]: Champion.model_validate(c) for c in blob.get("champions", [])}


def _load_items() -> dict[str, Item]:
    path = DATA_DIR / "items.json"
    if not path.exists():
        console.print(
            f"[red]Item data not found at {path}.[/red] "
            "Run [bold]arena scrape items[/bold] first."
        )
        raise typer.Exit(2)
    blob = json.loads(path.read_text())
    out: dict[str, Item] = {}
    for raw in blob.get("items", []):
        item = Item.model_validate(raw)
        out[item.name.lower()] = item
    return out


def _resolve_items(item_names: list[str], catalog: dict[str, Item]) -> list[Item]:
    resolved: list[Item] = []
    misses: list[str] = []
    for n in item_names:
        key = n.strip().lower()
        if not key:
            continue
        if key in catalog:
            resolved.append(catalog[key])
            continue
        # fuzzy: substring match
        candidates = [v for k, v in catalog.items() if key in k]
        if len(candidates) == 1:
            resolved.append(candidates[0])
        elif candidates:
            console.print(f"[yellow]Ambiguous item {n!r}: " +
                          ", ".join(c.name for c in candidates[:5]) + "[/yellow]")
            misses.append(n)
        else:
            misses.append(n)
    if misses:
        console.print(f"[red]Could not resolve: {', '.join(misses)}[/red]")
        raise typer.Exit(2)
    return resolved


# ---------- scrape ----------

@scrape_app.command("champions")
def scrape_champions_cmd(verbose: bool = typer.Option(False, "--verbose", "-v")) -> None:
    _configure_logging(verbose)
    champs = asyncio.run(scrape_champions.scrape_all())
    console.print(f"[green]✓[/green] Scraped {len(champs)} champions")


@scrape_app.command("items")
def scrape_items_cmd(verbose: bool = typer.Option(False, "--verbose", "-v")) -> None:
    _configure_logging(verbose)
    items = asyncio.run(scrape_items.scrape_all())
    console.print(f"[green]✓[/green] Scraped {len(items)} items")


@scrape_app.command("augments")
def scrape_augments_cmd(verbose: bool = typer.Option(False, "--verbose", "-v")) -> None:
    _configure_logging(verbose)
    augs = asyncio.run(scrape_augments.scrape_all())
    console.print(f"[green]✓[/green] Scraped {len(augs)} augments")


@scrape_app.command("runes")
def scrape_runes_cmd(verbose: bool = typer.Option(False, "--verbose", "-v")) -> None:
    _configure_logging(verbose)
    runes = asyncio.run(scrape_runes.scrape_all())
    console.print(f"[green]✓[/green] Scraped {len(runes)} runes")


@scrape_app.command("all")
def scrape_all_cmd(verbose: bool = typer.Option(False, "--verbose", "-v")) -> None:
    _configure_logging(verbose)

    async def _run() -> tuple[int, int, int, int]:
        return tuple(  # type: ignore[return-value]
            len(x)
            for x in await asyncio.gather(
                scrape_champions.scrape_all(),
                scrape_items.scrape_all(),
                scrape_augments.scrape_all(),
                scrape_runes.scrape_all(),
            )
        )

    c, i, a, r = asyncio.run(_run())
    console.print(f"[green]✓[/green] champions={c} items={i} augments={a} runes={r}")


# ---------- build ----------

@build_app.command("inspect")
def build_inspect(
    champ: str = typer.Option(..., "--champ", "-c", help="Champion key, e.g. Garen"),
    lvl: int = typer.Option(11, "--lvl", "-l", min=1, max=18),
    items: str = typer.Option("", "--items", "-i", help="Comma-separated item names"),
) -> None:
    """Show the final stat block for a champion + build."""
    champs = _load_champions()
    if champ not in champs:
        console.print(f"[red]Unknown champion {champ!r}.[/red] Examples: " +
                      ", ".join(list(champs)[:8]))
        raise typer.Exit(2)

    item_names = [s for s in items.split(",") if s.strip()]
    catalog = _load_items() if item_names else {}
    resolved = _resolve_items(item_names, catalog) if item_names else []

    stats = compose(champs[champ], level=lvl, items=resolved)

    table = Table(title=f"{champ} @ lvl {lvl}", show_header=False)
    table.add_column("stat", style="bold")
    table.add_column("value", justify="right")
    table.add_row("HP", f"{stats.hp:.0f} ({stats.base_hp:.0f} + {stats.bonus_hp:.0f})")
    table.add_row("AD", f"{stats.attack_damage:.1f} ({stats.base_ad:.0f} + {stats.bonus_ad:.0f})")
    table.add_row("AP", f"{stats.ability_power:.0f}")
    table.add_row("Armor", f"{stats.armor:.0f}")
    table.add_row("MR", f"{stats.mr:.0f}")
    table.add_row("AS", f"{stats.attack_speed:.3f}")
    table.add_row("Crit", f"{stats.crit_chance:.0%}")
    table.add_row("Ability Haste", f"{stats.ability_haste:.0f}")
    table.add_row("Lethality", f"{stats.lethality:.0f}")
    table.add_row("Movespeed", f"{stats.effective_movespeed:.0f}")

    if resolved:
        table.add_row("Items", ", ".join(i.name for i in resolved))
    console.print(table)


# ---------- dps ----------

def _print_breakdown(report) -> None:  # type: ignore[no-untyped-def]
    t = Table(title=f"vs {report.target}",
              caption=f"burst {report.ability_burst:.0f} · sustained {report.sustained_dps:.0f} DPS",
              show_lines=False)
    t.add_column("source")
    t.add_column("damage", justify="right")
    for k, v in report.breakdown.items():
        t.add_row(k, f"{v:.1f}")
    t.add_row("[bold]rotation window[/bold]", f"{report.rotation_time:.2f}s")
    t.add_row("[bold]autos in window[/bold]", f"{report.autos_in_window:.2f}")
    console.print(t)


@dps_app.command("run")
def dps_run(
    champ: str = typer.Option(..., "--champ", "-c"),
    lvl: int = typer.Option(11, "--lvl", "-l", min=1, max=18),
    items: str = typer.Option("", "--items", "-i"),
    target: str = typer.Option("all", "--target", "-t",
                               help="naked|squishy|bruiser|tank|all"),
    missing_hp: float = typer.Option(
        0.0, "--missing-hp",
        help="Fraction of target HP missing (0..1), used by execute spells.",
    ),
) -> None:
    """Compute auto-attack + ability DPS against target dummies."""
    champs = _load_champions()
    if champ not in champs:
        console.print(f"[red]Unknown champion {champ!r}.[/red]")
        raise typer.Exit(2)

    item_names = [s for s in items.split(",") if s.strip()]
    catalog = _load_items() if item_names else {}
    resolved = _resolve_items(item_names, catalog) if item_names else []

    stats = compose(champs[champ], level=lvl, items=resolved)
    abilities = get_abilities(champ)
    targets = list(DUMMIES.values()) if target == "all" else [DUMMIES[target.lower()]]

    if abilities is None:
        console.print(
            f"[yellow]No ability coefficients yet for {champ}.[/yellow] "
            f"Showing auto-attack DPS only. "
            f"Hand-curated champions: {', '.join(ability_keys()) or '(none)'}"
        )
        for d in targets:
            r = auto_dps(stats, d)
            console.print(
                f"  vs {d.name:8} → DPS [bold]{r.dps:.0f}[/bold] "
                f"(auto {r.auto_damage:.0f} × AS {r.attack_speed:.2f})"
            )
        return

    summary = Table(title=f"{champ} @ lvl {lvl} — items: {', '.join(i.name for i in resolved) or '(none)'}")
    summary.add_column("target")
    summary.add_column("burst", justify="right")
    summary.add_column("sustained DPS", justify="right")
    summary.add_column("auto/hit", justify="right")
    summary.add_column("AS", justify="right")

    for d in targets:
        r = full_rotation(abilities, stats, d, target_missing_hp_pct=missing_hp)
        summary.add_row(
            d.name,
            f"{r.ability_burst:.0f}",
            f"{r.sustained_dps:.0f}",
            f"{r.auto_damage_per_attack:.0f}",
            f"{stats.attack_speed:.2f}",
        )
    console.print(summary)


@dps_app.command("list-champions")
def dps_list() -> None:
    """List champions with hand-curated ability data."""
    keys = ability_keys()
    if not keys:
        console.print("[yellow]No ability data yet.[/yellow]")
        return
    console.print(f"Hand-curated champions ({len(keys)}): " + ", ".join(keys))


def main() -> None:  # pragma: no cover
    try:
        app()
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
