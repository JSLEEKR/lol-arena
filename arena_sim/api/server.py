"""FastAPI server: HTTP wrapper over the same engine the CLI uses.

Run with:
    pip install -e ".[api]"
    uvicorn arena_sim.api.server:app --reload

Endpoints:
    GET  /                       — index with version + mode list
    GET  /modes                  — game modes and their modifiers
    GET  /champions              — list champions (+ verified flag)
    GET  /items                  — list items
    GET  /augments               — list augments
    POST /build/inspect          — final stats for a build
    POST /dps                    — DPS vs target dummies
    POST /dps/compare            — A vs B side-by-side
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from arena_sim import __version__
from arena_sim.data.enrich_augments import enrich_augment
from arena_sim.data.enrich_items import enrich_item
from arena_sim.data.load_abilities import get as get_abilities
from arena_sim.data.load_abilities import load_all as load_abilities_all
from arena_sim.dps import DUMMIES, BuildSide, auto_dps, compare_dps, full_rotation, stat_diff
from arena_sim.models import Augment, Champion, Item
from arena_sim.modes import get_mode, list_modes
from arena_sim.stats import compose

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"


@lru_cache(maxsize=1)
def _champions() -> dict[str, Champion]:
    blob = json.loads((DATA_DIR / "champions.json").read_text())
    return {c["key"]: Champion.model_validate(c) for c in blob.get("champions", [])}


@lru_cache(maxsize=1)
def _items() -> dict[str, Item]:
    blob = json.loads((DATA_DIR / "items.json").read_text())
    out: dict[str, Item] = {}
    for raw in blob.get("items", []):
        item = enrich_item(Item.model_validate(raw))
        out[item.name.lower()] = item
    return out


@lru_cache(maxsize=1)
def _augments() -> dict[str, Augment]:
    blob = json.loads((DATA_DIR / "augments.json").read_text())
    raw_list = blob if isinstance(blob, list) else blob.get("augments", [])
    out: dict[str, Augment] = {}
    for raw in raw_list:
        aug = enrich_augment(Augment.model_validate(raw))
        out[aug.name.lower()] = aug
    return out


def _resolve_many(names: list[str], catalog: dict[str, Any], kind: str) -> list[Any]:
    out = []
    for n in names:
        key = n.strip().lower()
        if not key:
            continue
        if key in catalog:
            out.append(catalog[key])
            continue
        candidates = [v for k, v in catalog.items() if key in k]
        if len(candidates) == 1:
            out.append(candidates[0])
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Could not resolve {kind} {n!r}",
            )
    return out


# ---------------- Request / response models ----------------


class BuildRequest(BaseModel):
    champion: str = Field(..., description="DDragon key, e.g. 'Garen' or 'MonkeyKing'")
    level: int = Field(11, ge=1, le=18)
    items: list[str] = Field(default_factory=list)
    augments: list[str] = Field(default_factory=list)
    mode: str = Field("arena", description="rift | arena | urf")


class DpsRequest(BuildRequest):
    target: str = Field("all", description="naked | squishy | bruiser | tank | all")
    missing_hp_pct: float = Field(0.0, ge=0, le=1)


class CompareRequest(BaseModel):
    a: DpsRequest
    b: DpsRequest


# ---------------- App ----------------


app = FastAPI(
    title="arena-sim",
    version=__version__,
    description="LoL theorycrafting REST API.",
)


@app.get("/")
def index() -> dict[str, Any]:
    return {
        "name": "arena-sim",
        "version": __version__,
        "modes": [m.key.value for m in list_modes()],
        "champion_count": len(_champions()),
        "item_count": len(_items()),
        "augment_count": len(_augments()),
    }


@app.get("/modes")
def modes() -> list[dict[str, Any]]:
    return [
        {
            "key": m.key.value,
            "display_name": m.display_name,
            "attack_speed_cap": m.attack_speed_cap,
            "cooldown_multiplier": m.cooldown_multiplier,
            "cooldown_floor_sec": m.cooldown_floor_sec,
            "mana_cost_multiplier": m.mana_cost_multiplier,
            "hp_multiplier": m.hp_multiplier,
            "ad_multiplier": m.ad_multiplier,
            "augments_available": m.augments_available,
            "description": m.description,
        }
        for m in list_modes()
    ]


@app.get("/champions")
def champions(verified_only: bool = False) -> list[dict[str, Any]]:
    abilities = load_abilities_all()
    out = []
    for c in _champions().values():
        ab = abilities.get(c.key)
        verified = bool(ab and ab.verified)
        if verified_only and not verified:
            continue
        out.append({
            "key": c.key,
            "name": c.name,
            "title": c.title,
            "roles": c.roles,
            "verified": verified,
        })
    return out


@app.get("/items")
def items(search: str | None = None) -> list[dict[str, Any]]:
    s = search.lower() if search else None
    out = []
    for i in _items().values():
        if s and s not in i.name.lower():
            continue
        out.append({"id": i.id, "name": i.name, "cost": i.cost, "tags": i.tags})
    return out


@app.get("/augments")
def augments(search: str | None = None) -> list[dict[str, Any]]:
    s = search.lower() if search else None
    out = []
    for a in _augments().values():
        if s and s not in a.name.lower():
            continue
        out.append({
            "id": a.id, "name": a.name, "rarity": a.rarity.value,
            "description": a.description,
        })
    return out


def _resolve_inputs(req: BuildRequest) -> tuple[Champion, list[Item], list[Augment], Any]:
    champs = _champions()
    if req.champion not in champs:
        raise HTTPException(status_code=404, detail=f"Unknown champion: {req.champion}")
    try:
        mode_obj = get_mode(req.mode)
    except KeyError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    items = _resolve_many(req.items, _items(), "item")
    augments = _resolve_many(req.augments, _augments(), "augment")
    return champs[req.champion], items, augments, mode_obj


@app.post("/build/inspect")
def build_inspect(req: BuildRequest) -> dict[str, Any]:
    champ, items, augments, mode_obj = _resolve_inputs(req)
    s = compose(champ, level=req.level, items=items, augments=augments, mode=mode_obj)
    return {
        "champion": req.champion,
        "level": req.level,
        "mode": mode_obj.key.value,
        "stats": {
            "hp": s.hp, "base_hp": s.base_hp, "bonus_hp": s.bonus_hp,
            "attack_damage": s.attack_damage,
            "base_ad": s.base_ad, "bonus_ad": s.bonus_ad,
            "ability_power": s.ability_power,
            "armor": s.armor, "mr": s.mr,
            "attack_speed": s.attack_speed,
            "crit_chance": s.crit_chance, "crit_damage": s.crit_damage,
            "ability_haste": s.ability_haste,
            "lethality": s.lethality,
            "armor_pen_pct": s.armor_pen_pct,
            "magic_pen_flat": s.magic_pen_flat,
            "magic_pen_pct": s.magic_pen_pct,
            "lifesteal": s.lifesteal, "omnivamp": s.omnivamp,
            "movespeed": s.effective_movespeed,
        },
        "sources": s.sources,
    }


def _dps_payload(req: DpsRequest) -> dict[str, Any]:
    champ, items, augments, mode_obj = _resolve_inputs(req)
    s = compose(champ, level=req.level, items=items, augments=augments, mode=mode_obj)
    abilities = get_abilities(req.champion, mode_key=mode_obj.key.value)
    targets = (
        list(DUMMIES.values()) if req.target == "all"
        else [DUMMIES[req.target.lower()]]
    )
    rows = []
    for d in targets:
        if abilities is None or not abilities.has_any_damage_data():
            r = auto_dps(s, d, items=items)
            rows.append({
                "target": d.name,
                "dps": r.dps,
                "burst": 0,
                "auto_damage": r.auto_damage,
                "attack_speed": r.attack_speed,
                "data_quality": "auto-only",
            })
        else:
            r = full_rotation(abilities, s, d, target_missing_hp_pct=req.missing_hp_pct, items=items)
            rows.append({
                "target": d.name,
                "dps": r.sustained_dps,
                "burst": r.ability_burst,
                "auto_damage": r.auto_damage_per_attack,
                "attack_speed": s.attack_speed,
                "data_quality": "verified" if abilities.verified else "unverified",
            })
    return {
        "champion": req.champion,
        "level": req.level,
        "mode": mode_obj.key.value,
        "rows": rows,
    }


@app.post("/dps")
def dps(req: DpsRequest) -> dict[str, Any]:
    return _dps_payload(req)


@app.post("/dps/compare")
def dps_compare_endpoint(req: CompareRequest) -> dict[str, Any]:
    champ_a, items_a, augments_a, mode_a = _resolve_inputs(req.a)
    champ_b, items_b, augments_b, mode_b = _resolve_inputs(req.b)
    s_a = compose(champ_a, level=req.a.level, items=items_a, augments=augments_a, mode=mode_a)
    s_b = compose(champ_b, level=req.b.level, items=items_b, augments=augments_b, mode=mode_b)
    side_a = BuildSide(
        label=f"{req.a.champion} L{req.a.level}", stats=s_a,
        abilities=get_abilities(req.a.champion, mode_key=mode_a.key.value),
        items=items_a,
    )
    side_b = BuildSide(
        label=f"{req.b.champion} L{req.b.level}", stats=s_b,
        abilities=get_abilities(req.b.champion, mode_key=mode_b.key.value),
        items=items_b,
    )
    diff = stat_diff(s_a, s_b)
    rows = compare_dps(side_a, side_b, target_missing_hp_pct=req.a.missing_hp_pct)
    return {
        "a": {"champion": req.a.champion, "level": req.a.level, "mode": mode_a.key.value},
        "b": {"champion": req.b.champion, "level": req.b.level, "mode": mode_b.key.value},
        "stat_diff": {k: {"a": av, "b": bv, "delta": dv} for k, (av, bv, dv) in diff.items()},
        "dps_rows": [
            {
                "target": r.target,
                "a_dps": r.a_dps,
                "b_dps": r.b_dps,
                "delta": r.delta,
                "delta_pct": r.delta_pct,
            }
            for r in rows
        ],
    }
