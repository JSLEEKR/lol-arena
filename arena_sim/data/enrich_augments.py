"""Augment stat-effect enricher.

Many augments are just stat sticks ("Gain @AD@ Attack Damage").
Riot stores numeric values in `dataValues` (keyed by variable name like 'AD')
and templates them into the description with `@AD@` placeholders.

We:
  1. Resolve every @Var@ in the description to its dataValues[0] number.
  2. Run the resolved text through the same regex extractor used for items.
  3. Store extracted stats as augment.stat_effects.

Non-stat augments (procs, on-hit, conditional triggers) get empty stat_effects;
those need a separate event-effect layer that's not in scope yet.
"""

from __future__ import annotations

import re

from arena_sim.data.enrich_items import _RULES  # noqa: PLC2701  reuse same regex table
from arena_sim.models import Augment
from arena_sim.models.item import ItemStats

_VAR_RE = re.compile(r"@([A-Za-z0-9_]+)(\*[\d\.]+)?@")
_HTML_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _resolve_template(desc: str, values: dict[str, float]) -> str:
    """Replace @Var@ and @Var*K@ tokens with their numeric values."""

    def sub(m: re.Match[str]) -> str:
        var = m.group(1)
        mult = m.group(2)
        if var not in values:
            return m.group(0)
        v = values[var]
        if mult:
            try:
                v *= float(mult[1:])
            except ValueError:
                pass
        # Drop trailing .0 for integers
        return f"{int(v)}" if v.is_integer() else f"{v:g}"

    return _VAR_RE.sub(sub, desc)


def _strip_html(s: str) -> str:
    return _WS_RE.sub(" ", _HTML_RE.sub(" ", s)).strip()


def enrich_augment(aug: Augment) -> Augment:
    """Extract stat_effects from the augment's description + dataValues."""
    resolved = _resolve_template(aug.description, aug.data_values)
    text = _strip_html(resolved)
    extracted: dict[str, float] = {}
    for pat, field, scale in _RULES:
        m = pat.search(text)
        if not m:
            continue
        try:
            extracted[field] = max(extracted.get(field, 0.0), float(m.group(1)) * scale)
        except ValueError:
            continue
    if not extracted:
        return aug
    stats = ItemStats(**extracted)
    return aug.model_copy(update={"stat_effects": stats})


def enrich_all(augments: list[Augment]) -> list[Augment]:
    return [enrich_augment(a) for a in augments]
