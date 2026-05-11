"""Target dummy profiles representing typical opponent classes."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Dummy:
    name: str
    hp: float
    armor: float
    magic_resist: float
    description: str = ""


# Calibrated against typical LoL Arena round-5 totals (rough level 13-15 builds).
DUMMIES: dict[str, Dummy] = {
    "naked": Dummy(
        name="Naked",
        hp=1500,
        armor=0,
        magic_resist=0,
        description="Zero resists. Raw damage benchmark.",
    ),
    "squishy": Dummy(
        name="Squishy",
        hp=2200,
        armor=60,
        magic_resist=50,
        description="ADC / mage with one defensive item.",
    ),
    "bruiser": Dummy(
        name="Bruiser",
        hp=3200,
        armor=110,
        magic_resist=80,
        description="Fighter with 1.5 defensive items.",
    ),
    "tank": Dummy(
        name="Tank",
        hp=4500,
        armor=200,
        magic_resist=150,
        description="Full tank build.",
    ),
}


def get(name: str) -> Dummy:
    key = name.lower()
    if key not in DUMMIES:
        raise KeyError(f"Unknown dummy {name!r}. Choices: {list(DUMMIES)}")
    return DUMMIES[key]
