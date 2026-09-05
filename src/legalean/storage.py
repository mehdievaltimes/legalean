"""Loading/saving statutes and rules to/from JSON files. No LLM calls here."""

from __future__ import annotations

import json
from pathlib import Path

from .models import Rule, Statute


def load_statutes(path: str | Path) -> list[Statute]:
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    return [Statute.from_dict(d) for d in raw]


def load_rules(path: str | Path) -> list[Rule]:
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    return [Rule.from_dict(d["source_id"], d) for d in raw]


def save_rules(rules: list[Rule], path: str | Path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump([r.to_dict() for r in rules], f, indent=2)
        f.write("\n")
