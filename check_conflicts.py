#!/usr/bin/env python3
"""CLI: extract structured rules from statute excerpts, then FORMALLY VERIFY
conflicts between them by generating Lean 4 theorems and compiling them.

    python check_conflicts.py                  # use cached rules if present
    python check_conflicts.py --refresh         # re-run LLM extraction
    python check_conflicts.py --statutes path/to/statutes.json

Pipeline:
  1. Load rules (cached, or extracted via one Anthropic API call per excerpt
     -- see src/legalean/extract.py).
  2. Pure-Python candidate filtering (src/legalean/candidates.py, no LLM,
     no Lean): which pairs are structurally plausible conflicts?
  3. Generate a Lean 4 theorem per candidate (src/legalean/leangen.py).
  4. Compile each with `lake env lean` (src/legalean/leanverify.py). Only
     pairs Lean's kernel actually accepts a proof for are reported.

Requires the Lean toolchain (elan + lake) on PATH -- see README. Step 4
never calls the Anthropic API; only a missing rules cache (or --refresh)
triggers step 1's API call.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from legalean.candidates import find_candidates  # noqa: E402
from legalean.leangen import generate_conflict_files  # noqa: E402
from legalean.leanverify import verify_all  # noqa: E402
from legalean.models import Rule, Statute  # noqa: E402
from legalean.storage import load_rules, load_statutes, save_rules  # noqa: E402

DATA_DIR = Path(__file__).parent / "data"
LEAN_DIR = Path(__file__).parent / "lean"
LEAN_CONFLICTS_DIR = LEAN_DIR / "Legalean" / "Conflicts"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--statutes", default=str(DATA_DIR / "statutes.json"), help="path to statutes JSON")
    parser.add_argument("--rules-cache", default=str(DATA_DIR / "rules.json"), help="path to cached extracted rules")
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="re-run LLM extraction instead of using the rules cache (calls the Anthropic API)",
    )
    parser.add_argument(
        "--keep-lean-files",
        action="store_true",
        help="don't delete generated lean/Legalean/Conflicts/*.lean after the run (for inspection)",
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


def check_lean_toolchain() -> None:
    if shutil.which("lake") is None:
        print(
            "error: `lake` not found on PATH. This tool formally verifies conflicts with Lean 4 -- "
            "install it with elan (https://leanprover-community.github.io/get_started.html) and open a "
            "new shell, then re-run.",
            file=sys.stderr,
        )
        sys.exit(1)


def build_lean_library() -> None:
    """Compile lean/Legalean/Deontic.lean (+ smoke tests) so per-candidate
    files can import it. Cheap/no-op after the first run; no network access
    needed (no external Lean dependencies -- just core Lean's `omega`)."""
    proc = subprocess.run(["lake", "build"], cwd=LEAN_DIR, capture_output=True, text=True)
    if proc.returncode != 0:
        print("error: `lake build` failed for the lean/ project:\n" + proc.stdout + proc.stderr, file=sys.stderr)
        sys.exit(1)


def print_report(results, statutes_by_id: dict[str, Statute], n_candidates: int) -> None:
    verified = [r for r in results if r.verified]
    print(f"Checked {n_candidates} structural candidate(s); Lean formally verified {len(verified)} conflict(s):\n")

    if not verified:
        print("No conflicts survived formal verification.")
        return

    print("=" * 88)
    for i, result in enumerate(verified, start=1):
        a, b = result.generated.candidate.rule_a, result.generated.candidate.rule_b
        stmt_a, stmt_b = statutes_by_id[a.source_id], statutes_by_id[b.source_id]

        print(f"Conflict #{i}  (Lean theorem: {result.generated.theorem_name})")
        print("-" * 88)
        print(f"  Source A: {stmt_a.citation}")
        print(f"            {a.as_text()}")
        print(f"  Source B: {stmt_b.citation}")
        print(f"            {b.as_text()}")
        print()
        print(
            f"  Contradiction: {a.scope} says the activity is {a.action}, but {b.scope} says it is "
            f"{b.action}, for an overlapping case -- Lean formally verified these two rules, taken "
            f"together, are logically inconsistent."
        )
        print("=" * 88)


def main() -> None:
    args = parse_args()
    check_lean_toolchain()
    build_lean_library()

    statutes = load_statutes(args.statutes)
    statutes_by_id = {s.id: s for s in statutes}

    rules = get_rules(args, statutes)
    candidates = find_candidates(rules)

    generated = generate_conflict_files(candidates, statutes_by_id, LEAN_CONFLICTS_DIR)
    results = verify_all(generated, LEAN_DIR)

    print_report(results, statutes_by_id, len(candidates))

    if not args.keep_lean_files:
        for f in LEAN_CONFLICTS_DIR.glob("*.lean"):
            f.unlink()


if __name__ == "__main__":
    main()
