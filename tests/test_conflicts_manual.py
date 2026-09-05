#!/usr/bin/env python3
"""Manual, dependency-free sanity checks for the pure-Python conflict logic.

Not a pytest suite -- just asserts, runnable with plain `python3`. Verifies
core.conflicts against the shipped sample data (no LLM/API calls) and a
couple of hand-built edge cases (age-range overlap, non-overlapping ranges,
unrelated activities, same-jurisdiction non-conflict).

    python3 tests/test_conflicts_manual.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from legalean.conflicts import find_conflicts  # noqa: E402
from legalean.models import Condition, Rule  # noqa: E402
from legalean.storage import load_rules, load_statutes  # noqa: E402

DATA_DIR = Path(__file__).parent.parent / "data"


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


def test_sample_data_has_expected_conflicts():
    statutes = load_statutes(DATA_DIR / "statutes.json")
    rules = load_rules(DATA_DIR / "rules.json")
    assert {r.source_id for r in rules} == {s.id for s in statutes}, "rules.json must match statutes.json ids"

    conflicts = find_conflicts(rules)
    pairs = {frozenset({c.rule_a.source_id, c.rule_b.source_id}) for c in conflicts}
    assert frozenset({"us-csa-812", "ny-cannabis-law-222"}) in pairs
    assert frozenset({"us-csa-841", "ny-cannabis-law-222"}) in pairs
    assert len(conflicts) == 2, f"expected exactly 2 conflicts in the sample data, got {len(conflicts)}"


def test_classic_overlapping_age_gate_conflict():
    # "allowed if age >= 18" vs "prohibited if age < 21" -- ages 18-20 are contradictory.
    a = rule("a", "adult", "drinking alcohol", ("age", ">=", 18), "allowed", "US Federal")
    b = rule("b", "minor", "drinking alcohol", ("age", "<", 21), "prohibited", "US Federal")
    conflicts = find_conflicts([a, b])
    assert len(conflicts) == 1


def test_non_overlapping_age_ranges_do_not_conflict():
    # "allowed if age >= 21" vs "prohibited if age < 21" partition perfectly -- no overlap.
    a = rule("a", "adult", "possession of cannabis", ("age", ">=", 21), "allowed", "NY State")
    b = rule("b", "minor", "possession of cannabis", ("age", "<", 21), "prohibited", "NY State")
    assert find_conflicts([a, b]) == []


def test_same_action_is_not_a_conflict():
    a = rule("a", "any person", "possession of cannabis", (None, None, None), "prohibited", "US Federal")
    b = rule("b", "person under 21", "possession of cannabis", ("age", "<", 21), "prohibited", "NY State")
    assert find_conflicts([a, b]) == []


def test_unrelated_activities_do_not_conflict():
    a = rule("a", "any person", "possession of cannabis", (None, None, None), "prohibited", "US Federal")
    b = rule("b", "any person", "filing a tax return", ("day", ">=", 1), "required", "NY State")
    assert find_conflicts([a, b]) == []


def test_non_overlapping_scopes_do_not_conflict():
    a = rule("a", "any person", "jaywalking", (None, None, None), "prohibited", "California")
    b = rule("b", "any person", "jaywalking", (None, None, None), "allowed", "NY State")
    assert find_conflicts([a, b]) == []


def run_all():
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
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    run_all()
