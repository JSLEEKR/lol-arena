"""Test that per-mode ability data overrides baseline."""

from __future__ import annotations

from arena_sim.data.load_abilities import get


def test_baseline_returns_for_unknown_mode() -> None:
    base = get("Yasuo")
    urf = get("Yasuo", mode_key="urf")
    # Both should be non-None; if urf override exists, R cooldown will differ
    assert base is not None
    assert urf is not None


def test_urf_override_lower_r_cooldown_for_yasuo() -> None:
    base = get("Yasuo", mode_key="rift")
    urf = get("Yasuo", mode_key="urf")
    assert base is not None and urf is not None
    base_r = base.abilities["R"].cooldown
    urf_r = urf.abilities["R"].cooldown
    # URF overrides exist and bring R cooldown down (40/30/20 vs 70/50/30)
    assert urf_r[0] < base_r[0]


def test_falls_back_to_baseline_when_no_override() -> None:
    # Garen has no per-mode override → falls back to baseline
    base = get("Garen", mode_key="rift")
    urf = get("Garen", mode_key="urf")
    assert base is not None and urf is not None
    assert base.abilities["R"].cooldown == urf.abilities["R"].cooldown
