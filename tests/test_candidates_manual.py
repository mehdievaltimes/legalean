#!/usr/bin/env python3
"""Manual, dependency-free sanity checks for the pure-Python candidate filter.

Not a pytest suite -- just asserts, runnable with plain `python3`. Verifies
candidates.py (structural pre-filtering) against the shipped sample data and
a few hand-built edge cases. No LLM/API calls and no Lean/subprocess calls --
see test_lean_verification.py for the end-to-end formal-verification check.

    python3 tests/test_candidates_manual.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from legalean.candidates import find_candidates  # noqa: E402
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


def test_sample_data_has_expected_candidate():
    statutes = load_statutes(DATA_DIR / "statutes.json")
    rules = load_rules(DATA_DIR / "rules.json")
    assert {r.source_id for r in rules} == {s.id for s in statutes}, "rules.json must match statutes.json ids"

    candidates = find_candidates(rules)
    pairs = {frozenset({c.rule_a.source_id, c.rule_b.source_id}) for c in candidates}
    assert frozenset({"us-ina-employment-noncriminalization", "az-sb1070-5c"}) in pairs
    assert len(candidates) == 1, f"expected exactly 1 candidate in the sample data, got {len(candidates)}"


def test_classic_overlapping_age_gate_is_a_candidate_with_a_witness():
    # "allowed if age >= 18" vs "prohibited if age < 21" -- ages 18-20 are contradictory.
    a = rule("a", "adult", "drinking alcohol", ("age", ">=", 18), "allowed", "US Federal")
    b = rule("b", "minor", "drinking alcohol", ("age", "<", 21), "prohibited", "US Federal")
    candidates = find_candidates([a, b])
    assert len(candidates) == 1
    assert candidates[0].witness == 18


def test_non_overlapping_age_ranges_are_not_a_candidate():
    # "allowed if age >= 21" vs "prohibited if age < 21" partition perfectly -- no witness exists.
    a = rule("a", "adult", "possession of X", ("age", ">=", 21), "allowed", "Arizona State")
    b = rule("b", "minor", "possession of X", ("age", "<", 21), "prohibited", "Arizona State")
    assert find_candidates([a, b]) == []


def test_same_action_is_not_a_candidate():
    a = rule("a", "any person", "some activity", (None, None, None), "prohibited", "US Federal")
    b = rule("b", "some subset", "some activity", ("age", "<", 21), "prohibited", "Arizona State")
    assert find_candidates([a, b]) == []


def test_unrelated_activities_are_not_a_candidate():
    a = rule("a", "any person", "seeking unauthorized employment", (None, None, None), "allowed", "US Federal")
    b = rule("b", "any person", "filing a tax return", ("day", ">=", 1), "required", "Arizona State")
    assert find_candidates([a, b]) == []


def test_non_overlapping_scopes_are_not_a_candidate():
    a = rule("a", "any person", "jaywalking", (None, None, None), "prohibited", "California")
    b = rule("b", "any person", "jaywalking", (None, None, None), "allowed", "Arizona State")
    assert find_candidates([a, b]) == []


def test_different_condition_variables_are_not_a_candidate():
    # Same activity/scope/contradictory actions, but conditions on unrelated variables --
    # out of scope for this tool's condition model (see candidates.py docstring / README).
    a = rule("a", "any person", "some activity", ("age", ">=", 18), "allowed", "US Federal")
    b = rule("b", "any person", "some activity", ("income", "<", 50000), "prohibited", "US Federal")
    assert find_candidates([a, b]) == []


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
