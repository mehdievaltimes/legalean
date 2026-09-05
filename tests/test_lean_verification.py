#!/usr/bin/env python3
"""End-to-end check of the Lean formal-verification layer: generate Lean
theorems from candidates and actually compile them with `lake env lean`.

No LLM/API calls. Requires the Lean toolchain (elan + lake) on PATH -- see
README. This is the one script in tests/ that shells out (to `lake`, not to
any network service), so it's kept separate from test_candidates_manual.py.

    python3 tests/test_lean_verification.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from legalean.candidates import Candidate, find_candidates  # noqa: E402
from legalean.leangen import generate_conflict_files  # noqa: E402
from legalean.leanverify import verify_all  # noqa: E402
from legalean.models import Condition, Rule, Statute  # noqa: E402
from legalean.storage import load_rules, load_statutes  # noqa: E402

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
LEAN_DIR = ROOT / "lean"
SCRATCH_DIR = LEAN_DIR / "Legalean" / "ConflictsTestScratch"


def rule(source_id, subject, activity, condition, action, scope) -> Rule:
    var, op, val = condition
    return Rule(
        source_id=source_id,
        subject=subject,
        activity=activity,
        condition=Condition(variable=var, operator=op, value=val),
        action=action,
        scope=scope,
    )


def require_lean() -> None:
    if shutil.which("lake") is None:
        print("SKIP: `lake` not found on PATH -- install the Lean toolchain (see README) to run this test.")
        sys.exit(0)
    proc = subprocess.run(["lake", "build"], cwd=LEAN_DIR, capture_output=True, text=True)
    if proc.returncode != 0:
        print("FAIL: `lake build` failed:\n" + proc.stdout + proc.stderr)
        sys.exit(1)


def test_sample_data_conflicts_are_formally_verified():
    statutes = load_statutes(DATA_DIR / "statutes.json")
    statutes_by_id = {s.id: s for s in statutes}
    rules = load_rules(DATA_DIR / "rules.json")
    candidates = find_candidates(rules)
    assert len(candidates) == 2

    generated = generate_conflict_files(candidates, statutes_by_id, SCRATCH_DIR)
    results = verify_all(generated, LEAN_DIR)
    assert len(results) == 2
    for result in results:
        assert result.verified, f"Lean rejected a conflict expected to be provable: {result.stderr}"


def test_genuinely_non_overlapping_candidate_is_rejected_by_lean():
    # Bypass candidates.py's own overlap check (it wouldn't emit this pair) to confirm
    # Lean itself -- not just the Python heuristic -- refuses a false conflict claim.
    a = rule("a", "adult", "possession of X", ("age", ">=", 21), "allowed", "Arizona State")
    b = rule("b", "minor", "possession of X", ("age", "<", 21), "prohibited", "Arizona State")
    fake_candidate = Candidate(rule_a=a, rule_b=b, witness=21)  # 21 satisfies neither jointly
    statutes_by_id = {
        "a": Statute(id="a", jurisdiction="Arizona State", citation="test", raw_text="test"),
        "b": Statute(id="b", jurisdiction="Arizona State", citation="test", raw_text="test"),
    }
    generated = generate_conflict_files([fake_candidate], statutes_by_id, SCRATCH_DIR)
    results = verify_all(generated, LEAN_DIR)
    assert len(results) == 1
    assert not results[0].verified, "Lean should have rejected a witness that satisfies neither condition"


def run_all():
    require_lean()
    tests = [obj for name, obj in globals().items() if name.startswith("test_") and callable(obj)]
    failures = 0
    for t in tests:
        try:
            t()
            print(f"PASS: {t.__name__}")
        except AssertionError as e:
            failures += 1
            print(f"FAIL: {t.__name__}: {e}")
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    shutil.rmtree(SCRATCH_DIR, ignore_errors=True)
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    run_all()
