#!/usr/bin/env python3
"""CLI: extract structured rules from statute excerpts and report conflicts.

    python check_conflicts.py                  # use cached rules if present
    python check_conflicts.py --refresh         # re-run LLM extraction
    python check_conflicts.py --statutes path/to/statutes.json

Conflict detection (src/legalean/conflicts.py) is pure Python and never calls
the Anthropic API -- only --refresh (or a missing rules cache) does that.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from legalean.conflicts import find_conflicts  # noqa: E402
from legalean.models import Rule, Statute  # noqa: E402
from legalean.storage import load_rules, load_statutes, save_rules  # noqa: E402

DATA_DIR = Path(__file__).parent / "data"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--statutes", default=str(DATA_DIR / "statutes.json"), help="path to statutes JSON")
    parser.add_argument("--rules-cache", default=str(DATA_DIR / "rules.json"), help="path to cached extracted rules")
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="re-run LLM extraction instead of using the rules cache (calls the Anthropic API)",
    )
    return parser.parse_args()


def get_rules(args: argparse.Namespace, statutes: list[Statute]) -> list[Rule]:
    cache_path = Path(args.rules_cache)
    if not args.refresh and cache_path.exists():
        print(f"Loaded cached extracted rules from {cache_path} (use --refresh to re-run extraction).\n")
        return load_rules(cache_path)

    print(f"Calling the Anthropic API to extract rules from {len(statutes)} excerpt(s)...")
    from legalean.extract import DEFAULT_MODEL, extract_all  # imported lazily: no API key needed unless we get here

    print(f"Model: {DEFAULT_MODEL} (override with the LEGALEAN_MODEL env var)\n")
    try:
        rules = extract_all(statutes)
    except RuntimeError as e:
        print(f"Extraction failed: {e}", file=sys.stderr)
        sys.exit(1)
    save_rules(rules, cache_path)
    print(f"Cached extracted rules to {cache_path}\n")
    return rules


def print_conflicts_table(conflicts, statutes_by_id: dict[str, Statute]) -> None:
    if not conflicts:
        print("No structural conflicts detected among the extracted rules.")
        return

    print(f"Detected {len(conflicts)} conflict(s):\n")
    print("=" * 88)
    for i, conflict in enumerate(conflicts, start=1):
        a, b = conflict.rule_a, conflict.rule_b
        stmt_a, stmt_b = statutes_by_id[a.source_id], statutes_by_id[b.source_id]

        print(f"Conflict #{i}")
        print("-" * 88)
        print(f"  Source A: {stmt_a.citation}")
        print(f"            {a.as_text()}")
        print(f"  Source B: {stmt_b.citation}")
        print(f"            {b.as_text()}")
        print()
        print(f"  Contradiction: {conflict.explain()}")
        print("=" * 88)


def main() -> None:
    args = parse_args()
    statutes = load_statutes(args.statutes)
    statutes_by_id = {s.id: s for s in statutes}

    rules = get_rules(args, statutes)
    conflicts = find_conflicts(rules)
    print_conflicts_table(conflicts, statutes_by_id)


if __name__ == "__main__":
    main()
