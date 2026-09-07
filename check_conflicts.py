#!/usr/bin/env python3
"""CLI: read the markdown statute corpus and FORMALLY VERIFY conflicts
between the rules it declares, by generating Lean 4 theorems and compiling
them.

    python3 check_conflicts.py
    python3 check_conflicts.py --statutes path/to/statutes/
    python3 check_conflicts.py --keep-lean-files    # inspect generated proofs

Pipeline:
  1. Load hand-formalized rules from statutes/*.md (src/legalean/corpus.py).
  2. Pure-Python candidate filtering (src/legalean/candidates.py): which
     pairs are structurally plausible conflicts?
  3. Generate a Lean 4 theorem per candidate (src/legalean/leangen.py).
  4. Compile each with `lake env lean` (src/legalean/leanverify.py). Only
     pairs Lean's kernel actually accepts a proof for are reported.

No network access and no API key are required anywhere in this pipeline --
only the Lean toolchain (elan + lake). See src/legalean/extract.py for the
optional LLM-assisted drafting helper, which is not part of this path.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from legalean.candidates import PREEMPTION, find_candidates, find_near_miss_activities  # noqa: E402
from legalean.corpus import load_corpus  # noqa: E402
from legalean.leangen import generate_conflict_files  # noqa: E402
from legalean.leanverify import verify_all  # noqa: E402
from legalean.models import Statute  # noqa: E402

ROOT = Path(__file__).parent
STATUTES_DIR = ROOT / "statutes"
LEAN_DIR = ROOT / "lean"
LEAN_CONFLICTS_DIR = LEAN_DIR / "Legalean" / "Conflicts"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--statutes", default=str(STATUTES_DIR), help="directory of statute markdown files")
    parser.add_argument(
        "--keep-lean-files",
        action="store_true",
        help="don't delete generated lean/Legalean/Conflicts/*.lean after the run (for inspection)",
    )
    return parser.parse_args()


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
    needed (no external Lean dependencies -- just core Lean's `omega`).

    Generated conflict files sit inside the same Lake library glob, so any
    left over from a previous `--keep-lean-files` run would be compiled by
    this build -- and a stale or intentionally-unprovable one would fail it.
    They are regenerated from scratch every run, so clear them first.
    """
    for stale in LEAN_CONFLICTS_DIR.glob("*.lean"):
        stale.unlink()
    proc = subprocess.run(["lake", "build"], cwd=LEAN_DIR, capture_output=True, text=True)
    if proc.returncode != 0:
        print("error: `lake build` failed for the lean/ project:\n" + proc.stdout + proc.stderr, file=sys.stderr)
        sys.exit(1)


def warn_on_near_miss_activities(rules) -> None:
    """`activity` is an exact join key, so a near-but-unequal pair of keys is
    almost certainly a typo silently hiding a real conflict. Say so loudly
    rather than letting a similarity threshold guess."""
    near_misses = find_near_miss_activities(rules)
    if not near_misses:
        return
    print(
        f"warning: {len(near_misses)} pair(s) of activity keys look alike but are not equal, "
        f"so the rules carrying them will NOT be compared:",
        file=sys.stderr,
    )
    for activity_a, activity_b in near_misses:
        print(f"  - {activity_a!r}\n    {activity_b!r}", file=sys.stderr)
    print(
        "  Unify them if they name the same act, or reword them if they don't.\n",
        file=sys.stderr,
    )


def print_report(results, statutes_by_id: dict[str, Statute], n_rules: int, n_candidates: int) -> None:
    verified = [r for r in results if r.verified]
    print(
        f"Loaded {n_rules} formalized rule(s); {n_candidates} structural candidate(s); "
        f"Lean formally verified {len(verified)} conflict(s).\n"
    )

    if not verified:
        print("No conflicts survived formal verification.")
        return

    print("=" * 88)
    for i, result in enumerate(verified, start=1):
        a, b = result.generated.candidate.rule_a, result.generated.candidate.rule_b
        stmt_a, stmt_b = statutes_by_id[a.source_id], statutes_by_id[b.source_id]

        is_preemption = result.generated.candidate.kind == PREEMPTION
        label = "Field preemption" if is_preemption else "Contradiction"
        print(f"Conflict #{i}  [{label}]  (Lean theorem: {result.generated.theorem_name})")
        print("-" * 88)
        role_a, role_b = ("Occupies field", "Displaced") if is_preemption else ("Source A", "Source B")
        print(f"  {role_a}: {stmt_a.citation}")
        print(f"            {a.as_text()}")
        print(f"  {role_b}: {stmt_b.citation}")
        print(f"            {b.as_text()}")
        print()
        if is_preemption:
            print(
                f"  Field preemption: {a.scope} claims this field exclusively, while {b.scope} "
                f"also regulates it. The two are incompatible regardless of what the {b.scope} "
                f"rule says -- here both call the act {b.action}, and they still collide. Lean "
                f"formally verified the incompatibility."
            )
        else:
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

    statutes, rules = load_corpus(args.statutes)
    statutes_by_id = {s.id: s for s in statutes}

    warn_on_near_miss_activities(rules)

    candidates = find_candidates(rules)
    generated = generate_conflict_files(candidates, statutes_by_id, LEAN_CONFLICTS_DIR)
    results = verify_all(generated, LEAN_DIR)

    print_report(results, statutes_by_id, len(rules), len(candidates))

    if args.keep_lean_files:
        print(f"\nGenerated Lean proofs kept in {LEAN_CONFLICTS_DIR}")
    else:
        for f in LEAN_CONFLICTS_DIR.glob("*.lean"):
            f.unlink()


if __name__ == "__main__":
    main()
