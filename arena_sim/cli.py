"""arena CLI — entry point for scraping and (later) DPS calculation."""

from __future__ import annotations

import asyncio
import logging

import typer
from rich.console import Console
from rich.logging import RichHandler

from arena_sim.data import scrape_augments, scrape_champions, scrape_items, scrape_runes

console = Console()
app = typer.Typer(no_args_is_help=True, add_completion=False)
scrape_app = typer.Typer(no_args_is_help=True, help="Pull data from CommunityDragon.")
app.add_typer(scrape_app, name="scrape")


def _configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, show_path=False, markup=True)],
    )


@scrape_app.command("champions")
def scrape_champions_cmd(verbose: bool = typer.Option(False, "--verbose", "-v")) -> None:
    """Scrape all champions + stats + ability metadata."""
    _configure_logging(verbose)
    champs = asyncio.run(scrape_champions.scrape_all())
    console.print(f"[green]✓[/green] Scraped {len(champs)} champions")


@scrape_app.command("items")
def scrape_items_cmd(verbose: bool = typer.Option(False, "--verbose", "-v")) -> None:
    """Scrape all items (including arena prismatic)."""
    _configure_logging(verbose)
    items = asyncio.run(scrape_items.scrape_all())
    console.print(f"[green]✓[/green] Scraped {len(items)} items")


@scrape_app.command("augments")
def scrape_augments_cmd(verbose: bool = typer.Option(False, "--verbose", "-v")) -> None:
    """Scrape arena augments."""
    _configure_logging(verbose)
    augs = asyncio.run(scrape_augments.scrape_all())
    console.print(f"[green]✓[/green] Scraped {len(augs)} augments")


@scrape_app.command("runes")
def scrape_runes_cmd(verbose: bool = typer.Option(False, "--verbose", "-v")) -> None:
    """Scrape runes."""
    _configure_logging(verbose)
    runes = asyncio.run(scrape_runes.scrape_all())
    console.print(f"[green]✓[/green] Scraped {len(runes)} runes")


@scrape_app.command("all")
def scrape_all_cmd(verbose: bool = typer.Option(False, "--verbose", "-v")) -> None:
    """Scrape everything."""
    _configure_logging(verbose)

    async def _run() -> tuple[int, int, int, int]:
        champs, items, augs, runes = await asyncio.gather(
            scrape_champions.scrape_all(),
            scrape_items.scrape_all(),
            scrape_augments.scrape_all(),
            scrape_runes.scrape_all(),
        )
        return len(champs), len(items), len(augs), len(runes)

    c, i, a, r = asyncio.run(_run())
    console.print(f"[green]✓[/green] champions={c} items={i} augments={a} runes={r}")


if __name__ == "__main__":
    app()
