from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Rune(BaseModel):
    id: int
    name: str
    description: str = ""
    tree: str = ""  # "Precision", "Domination", ...
    slot: int = 0  # 0 = keystone, 1..3 = minor rows
    raw: dict[str, Any] = Field(default_factory=dict, exclude=True)
