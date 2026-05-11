"""FastAPI server smoke tests."""

from __future__ import annotations

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from arena_sim.api.server import app  # noqa: E402

client = TestClient(app)


def test_index() -> None:
    r = client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "arena-sim"
    assert "modes" in body
    assert body["champion_count"] > 0


def test_modes_endpoint() -> None:
    r = client.get("/modes")
    assert r.status_code == 200
    keys = [m["key"] for m in r.json()]
    assert "rift" in keys
    assert "arena" in keys
    assert "urf" in keys


def test_champions_listed() -> None:
    r = client.get("/champions")
    assert r.status_code == 200
    data = r.json()
    assert any(c["key"] == "Garen" for c in data)


def test_champions_verified_filter() -> None:
    r = client.get("/champions?verified_only=true")
    data = r.json()
    assert all(c["verified"] for c in data)
    assert any(c["key"] == "Garen" for c in data)


def test_build_inspect_endpoint() -> None:
    r = client.post("/build/inspect", json={
        "champion": "Garen",
        "level": 11,
        "items": ["Infinity Edge", "Stridebreaker"],
        "mode": "arena",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["stats"]["attack_damage"] > 69
    assert body["mode"] == "arena"


def test_dps_endpoint_arena_vs_urf() -> None:
    base = {"champion": "Garen", "level": 11, "items": ["Eclipse"]}
    arena = client.post("/dps", json={**base, "mode": "arena"}).json()
    urf = client.post("/dps", json={**base, "mode": "urf"}).json()
    arena_dps = next(r for r in arena["rows"] if r["target"] == "Bruiser")["dps"]
    urf_dps = next(r for r in urf["rows"] if r["target"] == "Bruiser")["dps"]
    assert urf_dps > arena_dps  # URF cooldown reduction → higher sustained


def test_dps_compare() -> None:
    r = client.post("/dps/compare", json={
        "a": {"champion": "Garen", "level": 11, "items": ["Infinity Edge"], "mode": "arena"},
        "b": {"champion": "Garen", "level": 11, "items": ["Eclipse,Black Cleaver".split(",")[0]], "mode": "arena"},
    })
    assert r.status_code == 200
    body = r.json()
    assert "stat_diff" in body
    assert "dps_rows" in body


def test_unknown_champion_returns_404() -> None:
    r = client.post("/dps", json={"champion": "NotAChampion", "level": 1})
    assert r.status_code == 404


def test_unknown_mode_returns_400() -> None:
    r = client.post("/dps", json={"champion": "Garen", "level": 11, "mode": "abyss"})
    assert r.status_code == 400
